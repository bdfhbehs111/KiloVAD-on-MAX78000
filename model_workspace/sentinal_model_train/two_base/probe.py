"""用 ai8xize 的整型仿真做判别力验收：每个 npy 跑一次合成，解 sampleoutput.h。

为什么必须用这个而不是 ai8x.simulate
======================================================================================
ai8x.simulate 是 QAT 口径（simulate 模式跳过 out_shift -= activation_threshold），
对 --clip-method SCALE 出来的 checkpoint 会算出恒等输出。只有 ai8xize 生成的
sampleoutput.h 反映板上真正会发生的事（E2.5 踩过这个坑：全零输入和真人声给出同一个值）。

三条验收（顺序不能换）
======================================================================================
1. 全零输入 与 真实人声 的 margin 必须不同
2. 同一类的不同样本，margin 不能全一样
3. 上面两条过了才看 k 的标定

用法
    python probe.py --ckpt two_base_qat-q.pth.tar --samples EXT_zero voice0_k16 ...
    python probe.py --ckpt ... --grid          # 扫 k：voice0/noise0 的 k=4..64
    python probe.py --ckpt ... --kat           # 只跑 KAT 样本（挑一个 voice 出 sampleoutput）
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR.parent
SYNTH = Path(r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent"
             r"\max78000_backup\ai8x-synthesis")
DISTILLER = MODEL_DIR / "ai8x-training" / "distiller-repo"
GIN = MODEL_DIR / "one_base_withqat" / "_gin"
PY = sys.executable


def decode(out_h: Path):
    """从 sampleoutput.h 解出 (raw, s0, s1, margin)。

    ai8xize 实际写的是：
        #define SAMPLE_OUTPUT { \\
          0x50404000, 0x0000ffff, 0x00000001, 0x000002f0, 0x00000000 \\
        }
    第 0 项=输出地址，第 1 项=掩码，第 2 项=**输出字个数**，第 3 项起才是输出字。
    （README_PLUG.md 里写成 `..., 1, 0x000002f0` 是同一个东西的十进制写法。）

    板上 unload 把两个 int8 写进 consecutive uint16，于是 app 读 uint32 时看到的是
    字节 [b0 00 b1 00]，所以 app 用 `& 0xff` 和 `>> 16` 取两个类。

    但 **sampleoutput.h 里的 raw 是 AI85 的输出字**，两个类紧挨着：b0=类0、b1=类1。
    例：sen1 的 KAT raw=0x000002f0 -> s0=int8(0xf0)=-16、s1=int8(0x02)=+2、
    margin=-18，与 README_PLUG.md 记的 −18 逐位一致。**别照抄 app 的 >>16**。
    """
    txt = out_h.read_text(encoding="utf-8", errors="replace")
    nums = [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]+)", txt)]
    if len(nums) < 4:
        return None
    val = nums[3]

    def s8(b):
        return b - 256 if b >= 128 else b

    s0 = s8(val & 0xff)
    s1 = s8((val >> 8) & 0xff)
    return val, s0, s1, s0 - s1


def run_one(ckpt: Path, yaml: Path, npy: Path, tag: str, keep: bool):
    test_dir = (BASE_DIR / "_probe" / tag) if keep else (BASE_DIR / "_probe_tmp")
    if test_dir.exists():
        # 用 rmtree：ai8xize 生成的 weights.h 等文件偶尔还被句柄占着，逐个 unlink 会
        # WinError 32。ignore_errors 让它能自己重试，剩下的 --overwrite 会覆盖。
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    out_h = test_dir / "vad_cnn" / "sampleoutput.h"
    if out_h.exists():
        out_h.unlink()

    cmd = [PY, str(SYNTH / "ai8xize.py"),
           "--device", "MAX78000",
           "--config-file", str(yaml),
           "--checkpoint-file", str(ckpt),
           "--prefix", "vad_cnn",
           "--test-dir", str(test_dir),
           "--sample-input", str(npy),
           "--no-version-check", "--overwrite"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(DISTILLER) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    # 必须在 ai8x-synthesis 根目录下跑：izer/assets.py:143 用相对路径
    # 'assets/vscode/defaults/settings.json'，换 cwd 就 FileNotFoundError。
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8",
                       errors="replace", cwd=str(SYNTH))
    secs = time.time() - t0
    if r.returncode != 0:
        print(f"[FAIL] {tag}: ai8xize 返回 {r.returncode}")
        print((r.stderr or r.stdout or "")[-2500:])
        return None
    if not out_h.is_file():
        print(f"[FAIL] {tag}: 没生成 {out_h}")
        print((r.stdout or "")[-1500:])
        return None
    dec = decode(out_h)
    if dec is None:
        print(f"[FAIL] {tag}: sampleoutput.h 解析失败")
        return None
    val, s0, s1, margin = dec
    print(f"{tag:22s} raw=0x{val:08x}  s0={s0:4d}  s1={s1:4d}  "
          f"margin={margin:4d}  {secs:5.1f}s  {'WHISPER' if margin < 0 else 'non'}")
    return dict(tag=tag, raw=val, s0=s0, s1=s1, margin=margin, secs=secs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True, help="quantize.py 产出的 -q checkpoint")
    ap.add_argument("--yaml", default=str(BASE_DIR / "vad_cnn.yaml"))
    ap.add_argument("--samples", nargs="*", default=None, help="_gin 里的 npy 名（不带 .npy）")
    ap.add_argument("--grid", action="store_true", help="扫 k ∈ {4,8,16,32,64} 的 voice0/noise0")
    ap.add_argument("--keep", action="store_true", help="保留每个样本的合成目录（拿 cnn.c 用）")
    args = ap.parse_args()

    ckpt = Path(args.ckpt).resolve()
    yaml = Path(args.yaml).resolve()
    if not ckpt.is_file():
        sys.exit(f"找不到 {ckpt}")

    if args.grid:
        names = [f"{t}{j}_k{k}" for t in ("voice", "noise") for j in (0, 1)
                 for k in (4, 8, 16, 32, 64)]
    elif args.samples:
        names = args.samples
    else:
        names = ["EXT_zero", "EXT_pos127", "EXT_neg128", "EXT_alt",
                 "voice0_k16", "voice1_k16", "voice2_k16", "voice3_k16",
                 "noise0_k16", "noise1_k16", "noise2_k16", "noise3_k16"]

    print(f"ckpt  {ckpt}")
    print(f"yaml  {yaml}")
    print(f"{len(names)} 个样本\n")
    rows = []
    for n in names:
        npy = GIN / f"{n}.npy"
        if not npy.is_file():
            print(f"[跳过] {npy} 不存在")
            continue
        r = run_one(ckpt, yaml, npy, n, args.keep)
        if r:
            rows.append(r)

    if not rows:
        return
    # ---- 三条验收 ----
    print("\n=== 验收 ===")
    by = {r["tag"]: r["margin"] for r in rows}
    zero = by.get("EXT_zero")
    voices = [r["margin"] for r in rows if r["tag"].startswith("voice")]
    noises = [r["margin"] for r in rows if r["tag"].startswith("noise")]
    if zero is not None and voices:
        ok1 = all(v != zero for v in voices)
        print(f"1) 全零={zero:4d} vs 人声{voices} -> "
              + ("通过（不同）" if ok1 else "**失败：全零与真实样本输出相同 = 网络被偏置支配**"))
    else:
        ok1 = None
        print("1) 缺少 EXT_zero 或 voice 样本，跳过")
    if len(voices) > 1:
        ok2 = len(set(voices)) > 1
        print(f"2) 同类不同样本 {voices} -> "
              + ("通过（有差异）" if ok2 else "**失败：同类样本输出全一样**"))
    else:
        ok2 = None
        print("2) 人声样本不足 2 个，跳过")
    if voices and noises:
        print(f"3) 判别方向：人声 {voices} / 非人声 {noises}")
        print(f"   人声 <=0 的个数 {sum(1 for v in voices if v < 0)}/{len(voices)}，"
              f"非人声 >0 的个数 {sum(1 for v in noises if v > 0)}/{len(noises)}")
    if ok1 and ok2:
        print("\n判据 1/2 通过 -> 可以看 accuracy 和 k 标定。")


if __name__ == "__main__":
    main()
