"""E4d —— 自蒸馏：teacher = 未剪枝浮点原模型，student = 剪枝后模型

======================================================================================
配方（按你的给定）
======================================================================================
    teacher = ai8x-training/logs/one_base___2026.11.03-182532/one_base_best.pth.tar
              （未剪枝浮点原模型，eval + no_grad，权重冻结）
    student = one_base_prune/prune_e4b/ckpts/trial_0007.pth.tar
              （t7: 32-24-32-16-8-16，10,784 B，38,016 cycles，−67.9%
               它已经过了 5ep 的 CE 微调，所以蒸馏起点是"伤口恢复过一轮"的模型，
               不是刚剪完的残废网络。换起点用 --student <path>，
               想回到刚剪完的状态用 --from-base）
    loss    = alpha * CE(student_logits, y)
            + (1 - alpha) * KL( log_softmax(s/T) || softmax(t/T) ) * T^2
    epochs  = 8        T = 3        alpha = 0.7
    lr      = 3e-4     Adam + weight_decay 1e-4

======================================================================================
为什么必须同时跑一支 CE-only 对照
======================================================================================
E4b 的 40 个 trial 全是 CE-only。如果这里只跑 KD，拿到一个数就无法回答
「蒸馏到底赚了多少」—— 因为换个 seed 就能差 0.001（E4b 的不剪对照组自己就掉了
0.0009）。所以每个 (配置, seed) 都成对跑：
        mode=kd   alpha*CE + (1-alpha)*KL*T^2
        mode=ce   CE（等价 alpha=1）
两者共用同一个 seed、同一份剪枝起点、同一套数据顺序。**只有成对差值可读。**

======================================================================================
单 seed 不报结论
======================================================================================
--seeds N 对每个 (配置, mode) 跑 N 个独立 seed，报 mean 和 [min,max]。
本脚本不打印「A 比 B 好」，只打印配对差值 mean±range —— 判断留给人。

======================================================================================
产出（--out，默认本目录）
======================================================================================
    distill.csv     每 (配置, mode, seed) 一行，边跑边 flush
    distill.txt     原始行 + 按 (配置, mode) 汇总 + 配对差值 kd−ce
    ckpts/*.pth.tar 每个训练完的 student（含 KD 的），可直接喂 E6 的 QAT
    manifest.json   配方 / teacher 路径 / 剪枝入口 / 时间戳

======================================================================================
用法
======================================================================================
    python distill.py --smoke                      # 门禁：1 ep × 4096 条 × 1 seed
    python distill.py                              # 默认 t7 ckpt 起点，kd+ce，3 seed
    python distill.py --from-base                  # 起点改成"刚剪完"（与 E4b 同一状态）
    python distill.py --student ...trial_0022.pth.tar   # 换学生起点
    python distill.py --trial 7 37 22 --from-base  # 三个 <20 KB 配置从原模型剪
    python distill.py --channels 32 24 32 16 8 16  # 自定义通道（4 的倍数）
    python distill.py --alpha 0.5 --T 2            # 扫配方
    python distill.py --report                     # 只把已有 csv 打成表

判据：同一个 seed 下 kd 与 ce 的 auc_val 差值，要明显大于 seed 间的 range。
"""

import argparse
import csv
import importlib.util
import json
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

BASE_DIR = Path(__file__).resolve().parent
PRUNE_DIR = BASE_DIR.parent / "one_base_prune"

# ---------------------------------------------------------------------------
# 判据 / 剪枝入口 / 数据集 全部复用 one_base_prune，不另写一份。
#
# 坑：optuna_search.py 内部自己又会按路径加载一份 prunning.py。若本文件也单独
# 加载一次 prunning，就存在**两个 prunning 模块实例**，set_checkpoint 只改到其中
# 一个，teacher 路径与 student 构造就会串味。所以只加载 optuna_search，再从它身上
# 取 P —— 全脚本共用同一个 prunning 实例。
# ---------------------------------------------------------------------------
if not PRUNE_DIR.is_dir():
    sys.exit(f"[路径] 找不到 {PRUNE_DIR}，本脚本必须与 one_base_prune/ 同级")


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E4 = _load_by_path("e4_search", PRUNE_DIR / "optuna_search.py")
P = E4.P                                          # 唯一的 prunning 实例

E4_RESULTS = PRUNE_DIR / "prune_e4b" / "results.csv"
# 默认学生 = E4b 前沿最省的那个点（t7, 10,784 B / 38,016 cycles / 32-24-32-16-8-16）。
# 它是「已剪枝 + 已 CE 微调 5ep」的权重，所以蒸馏的起点是"伤口已经恢复过一轮"，
# 不是"刚剪完的残废模型"。想回到刚剪完的起点用 --from-base。
DEFAULT_STUDENT = PRUNE_DIR / "prune_e4b" / "ckpts" / "trial_0007.pth.tar"
BATCH = P.BATCH

FIELDS = [
    "run_id", "ts", "tag", "channels", "weight_bytes", "cycles", "macs", "proc_passes",
    "mode", "T", "alpha", "epochs", "lr", "seed",
    "auc_val", "fpr_val", "tpr_val", "auc_test", "fpr_test", "tpr_test", "top1_test",
    "seconds", "ckpt",
]


# --------------------------------------------------------------------------- #
# 模型
# --------------------------------------------------------------------------- #
def build_teacher(device, path=None):
    """未剪枝浮点原模型。eval + requires_grad_(False)，不参与优化。"""
    if path:
        P.set_checkpoint(path)
    model, epoch = P.build_model(device)
    model.eval()
    for prm in model.parameters():
        prm.requires_grad_(False)
    return model, epoch


def channels_from_results(trial_ids):
    """从 E4b 的 results.csv 读通道配置。"""
    if not E4_RESULTS.is_file():
        sys.exit(f"[trial] 找不到 {E4_RESULTS}")
    rows = {r["trial"]: r for r in csv.DictReader(open(E4_RESULTS, encoding="utf-8"))}
    out = []
    for t in trial_ids:
        key = str(t)
        if key not in rows:
            sys.exit(f"[trial] results.csv 里没有 trial {key}")
        out.append((f"t{key}", [int(rows[key][f"ch{i}"]) for i in range(1, 7)]))
    return out


def read_student_ckpt(path):
    """读一个已剪枝的 ckpt，返回 (tag, channels, ckpt dict)。

    tag 从文件名推：trial_0007.pth.tar -> t7；其它名字就原样用 stem。
    """
    path = Path(path).resolve()
    if not path.is_file():
        sys.exit(f"[student] 找不到 {path}")
    ck = torch.load(path, map_location="cpu", weights_only=False)
    if "state_dict" not in ck or "channels" not in ck:
        sys.exit(f"[student] {path.name} 里没有 state_dict / channels，不是 E4b 的 ckpt")
    m = re.match(r"^trial_(\d+)$", path.name.replace(".pth.tar", ""))
    tag = f"t{int(m.group(1))}" if m else path.name.replace(".pth.tar", "")
    return tag, [int(c) for c in ck["channels"]], ck


def make_student(channels, device, ckpt=None):
    """构造学生。ckpt 给了就从那里载权重（channels 必须是它的形状）。

    先按 E4.build_pruned 建出同通道数的模型（剪枝是确定性的，形状必然对得上），
    再 load_state_dict 覆盖成 ckpt 里的权重 —— 这样"从同一剪枝入口构造"和
    "从已训练权重出发"两件事兼得，state_dict 里的量化标量也一起载入。
    """
    model = E4.build_pruned(channels, device)
    if ckpt is not None:
        try:
            model.load_state_dict(ckpt["state_dict"])
        except RuntimeError as exc:
            sys.exit(f"[student] 权重与通道 {channels} 形状不匹配：\n{exc}")
    model.eval()
    return model


# --------------------------------------------------------------------------- #
# 蒸馏损失
# --------------------------------------------------------------------------- #
def kd_loss(student_logits, teacher_logits, target, T, alpha):
    """alpha*CE + (1-alpha)*KL(log_softmax(s/T) || softmax(t/T)) * T^2

    KL 必须用 batchmean：PyTorch 的 kl_div 默认 'mean' 是逐元素平均，会再除以
    类别数(2)，量纲和 CE 对不上，T^2 补不回来。
    """
    ce = F.cross_entropy(student_logits, target)
    kl = F.kl_div(F.log_softmax(student_logits / T, dim=1),
                  F.softmax(teacher_logits / T, dim=1),
                  reduction="batchmean") * (T * T)
    return alpha * ce + (1.0 - alpha) * kl, ce.detach(), kl.detach()


# --------------------------------------------------------------------------- #
# 训练
# --------------------------------------------------------------------------- #
def train_student(student, teacher, loader, device, epochs, lr, T, alpha, mode, tag=""):
    """mode='kd' 走蒸馏；mode='ce' 只走 CE。

    teacher 每步 live forward，而不是预计算 logits 缓存：训练集带在线增强
    （np.roll ±10 块），缓存下来的 teacher 输出对应的输入和 student 当步看到的
    不是同一张图。多一次前向远小于数据加载开销（每 epoch ~63 s 是瓶颈）。
    """
    student.train()
    optimizer = torch.optim.Adam(student.parameters(), lr=lr, weight_decay=1e-4)
    use_kd = (mode == "kd")
    hist = []
    for ep in range(epochs):
        t0 = time.time()
        total = correct = 0
        ce_sum = kl_sum = loss_sum = 0.0
        for inputs, labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            s = student(inputs)
            if use_kd:
                with torch.no_grad():
                    t = teacher(inputs)
                loss, ce, kl = kd_loss(s, t, labels, T, alpha)
                kl_sum += float(kl) * labels.size(0)
            else:
                loss = F.cross_entropy(s, labels)
                ce = loss.detach()
            loss.backward()
            optimizer.step()
            # 必须 detach 再取标量：KD 分支的 loss 带 grad，float(loss) 会触发
            # UserWarning「Converting a tensor with requires_grad=True to a scalar」
            loss_sum += float(loss.detach()) * labels.size(0)
            ce_sum += float(ce) * labels.size(0)
            correct += (s.argmax(1) == labels).sum().item()
            total += labels.size(0)
        rec = dict(ep=ep + 1, loss=loss_sum / total, ce=ce_sum / total,
                   kl=(kl_sum / total) if use_kd else float("nan"),
                   top1=100 * correct / total, sec=time.time() - t0)
        hist.append(rec)
        print(f"      {tag}ep[{ep + 1}/{epochs}]  loss={rec['loss']:.4f}  "
              f"ce={rec['ce']:.4f}" + (f"  kl={rec['kl']:.5f}" if use_kd else "") +
              f"  top1={rec['top1']:6.2f}%  {rec['sec']:5.1f}s", flush=True)
    student.eval()
    return hist


# --------------------------------------------------------------------------- #
# CSV / 报告
# --------------------------------------------------------------------------- #
def read_rows(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_row(csv_path, row):
    csv_path = Path(csv_path)
    new_file = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDS})
        f.flush()
    csv_path.with_name("distill.txt").write_text(
        format_report(read_rows(csv_path)) + "\n", encoding="utf-8")


def _f(r, k, default=float("nan")):
    v = r.get(k)
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def summarize(rows):
    """按 (tag, mode) 汇总 seeds：mean / min / max。"""
    groups = {}
    for r in rows:
        groups.setdefault((r["tag"], r["mode"]), []).append(r)
    out = []
    for (tag, mode), rs in groups.items():
        def col(k):
            return [_f(r, k) for r in rs if not math.isnan(_f(r, k))]
        av, at = col("auc_val"), col("auc_test")
        fv, ft = col("fpr_val"), col("fpr_test")
        if not av:
            continue
        out.append(dict(
            tag=tag, mode=mode, n=len(rs),
            ch=rs[0]["channels"], W=int(_f(rs[0], "weight_bytes")),
            cycles=int(_f(rs[0], "cycles")),
            av=sum(av) / len(av), av_lo=min(av), av_hi=max(av),
            at=sum(at) / len(at), at_lo=min(at), at_hi=max(at),
            fv=sum(fv) / len(fv), fv_lo=min(fv), fv_hi=max(fv),
            ft=sum(ft) / len(ft), ft_lo=min(ft), ft_hi=max(ft),
            sec=sum(col("seconds")) / max(len(rs), 1)))
    return out


def format_report(rows):
    if not rows:
        return "没有数据。"
    hdr = (f"{'tag':6s} {'mode':4s} {'ch1..ch6':>19s} {'W_B':>6s} {'cycles':>7s} "
           f"{'AUC val':>17s} {'AUC test':>17s} {'FPR val':>17s} {'FPR test':>17s} {'sec':>5s}")
    lines = ["=== 每次训练（一行一个 seed）===", hdr, "-" * len(hdr)]
    for tag in sorted({r["tag"] for r in rows}):
        for mode in ("init", "ce", "kd"):
            rs = sorted([r for r in rows if r["tag"] == tag and r["mode"] == mode],
                        key=lambda r: _f(r, "seed"))
            for r in rs:
                sd = "—" if r["mode"] == "init" else f"s{int(_f(r, 'seed'))}"
                lines.append(
                    f"{tag:6s} {mode:4s} {r['channels']:>19s} "
                    f"{int(_f(r, 'weight_bytes')):6d} {int(_f(r, 'cycles')):7d} "
                    f"{_f(r, 'auc_val'):.5f}{'':>10s} {_f(r, 'auc_test'):.5f}{'':>10s} "
                    f"{_f(r, 'fpr_val'):.4f}{'':>12s} {_f(r, 'fpr_test'):.4f}{'':>12s} "
                    f"{_f(r, 'seconds'):5.0f}  {sd}")

    lines += ["", "=== 按 (配置, mode) 汇总 seeds（± 是半极差）===", hdr, "-" * len(hdr)]
    agg = summarize(rows)
    for s in sorted(agg, key=lambda s: (s["tag"], s["mode"])):
        lines.append(
            f"{s['tag']:6s} {s['mode']:4s} {s['ch']:>19s} {s['W']:6d} {s['cycles']:7d} "
            f"{s['av']:.5f}±{(s['av_hi'] - s['av_lo']) / 2:.5f} "
            f"{s['at']:.5f}±{(s['at_hi'] - s['at_lo']) / 2:.5f} "
            f"{s['fv']:.4f}[{s['fv_lo']:.4f},{s['fv_hi']:.4f}] "
            f"{s['ft']:.4f}[{s['ft_lo']:.4f},{s['ft_hi']:.4f}] {s['sec']:5.0f} n={s['n']}")

    lines += ["", "=== 配对差值 kd − ce（同一个 seed，同一起点）==="]
    byc = {}
    for r in rows:
        if r["mode"] in ("kd", "ce"):
            byc.setdefault((r["tag"], int(_f(r, "seed"))), {})[r["mode"]] = r
    pairs = {}
    for (tag, _seed), d in byc.items():
        if "kd" in d and "ce" in d:
            pairs.setdefault(tag, []).append(
                (_f(d["kd"], "auc_val") - _f(d["ce"], "auc_val"),
                 _f(d["kd"], "auc_test") - _f(d["ce"], "auc_test"),
                 _f(d["kd"], "fpr_val") - _f(d["ce"], "fpr_val"),
                 _f(d["kd"], "fpr_test") - _f(d["ce"], "fpr_test")))
    if not pairs:
        lines.append("  （还没有成对的 kd/ce 结果）")
    else:
        lines.append(f"{'tag':6s} {'n':>2s} {'dAUCval':>10s} {'range':>20s} "
                     f"{'dAUCtest':>10s} {'dFPRval':>10s} {'dFPRtest':>10s}")
        for tag, ps in sorted(pairs.items()):
            n = len(ps)
            dv = [p[0] for p in ps]
            dt = [p[1] for p in ps]
            lines.append(
                f"{tag:6s} {n:2d} {sum(dv) / n:+10.5f} "
                f"[{min(dv):+.5f},{max(dv):+.5f}] {sum(dt) / n:+10.5f} "
                f"{sum(p[2] for p in ps) / n:+10.4f} {sum(p[3] for p in ps) / n:+10.4f}")
        lines += ["",
                  "判据：|dAUCval| 均值要明显大于 range 宽度的一半，才算蒸馏真的有用。",
                  "只跑 1 个 seed 时 range 恒为 0，这一行没有意义。"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="E4d 自蒸馏（teacher=未剪枝浮点原模型）",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--student", default=None,
                    help="学生 ckpt（已剪枝/已微调）。默认 = "
                         "one_base_prune/prune_e4b/ckpts/trial_0007.pth.tar")
    ap.add_argument("--from-base", dest="from_base", action="store_true",
                    help="不用 --student，改为从 one_base 原模型现场剪枝（刚剪完的起点）")
    ap.add_argument("--trial", type=int, nargs="+", default=None,
                    help="从 E4b 的 results.csv 取通道配置，可多个（如 --trial 7 37 22）")
    ap.add_argument("--channels", type=int, nargs=6, default=None,
                    help="直接给 6 个通道数（必须是 4 的倍数）")
    ap.add_argument("--tag", default=None,
                    help="覆盖结果里的 tag（同一份配置跑两支不同起点时用来区分）")
    ap.add_argument("--teacher", default=None,
                    help="teacher ckpt 路径（默认 = one_base___2026.11.03-182532/one_base_best.pth.tar）")
    ap.add_argument("--T", type=float, default=3.0, help="蒸馏温度（建议 2~4）")
    ap.add_argument("--alpha", type=float, default=0.7,
                    help="CE 权重；KD 权重 = 1-alpha（剪得狠取 0.7）")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--modes", nargs="+", default=["kd", "ce"], choices=["kd", "ce"],
                    help="跑哪些模式。成对才有意义；只跑 kd 得不到可读结论")
    ap.add_argument("--device", default="cuda", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--limit", type=int, default=0, help="调试用：等间距抽样这么多条")
    ap.add_argument("--out", default=".", help="产出目录（默认 = 本目录）")
    ap.add_argument("--report", action="store_true", help="只读 csv 出表，不训练")
    ap.add_argument("--smoke", action="store_true", help="门禁：1 ep × 4096 条 × 1 seed")
    args = ap.parse_args()

    out_dir = (BASE_DIR / args.out).resolve()
    csv_path = out_dir / "distill.csv"
    ckpt_dir = out_dir / "ckpts"

    if args.report:
        print(format_report(read_rows(csv_path)))
        return

    # ---- 目标配置 / 学生起点 ----
    #   --student 给定时：目标 = 该 ckpt 的通道配置，起点 = 该 ckpt 的权重
    #   --trial / --channels 且不给 --student：从 one_base 原模型现场剪枝（刚剪完的起点）
    student_ck = None
    if args.channels:
        cands = [("custom", list(args.channels))]
        if args.student:
            _tag, chs, student_ck = read_student_ckpt(args.student)
            if chs != list(args.channels):
                sys.exit(f"[student] --channels {args.channels} 与 ckpt 里的 {chs} 不一致")
    elif args.trial:
        cands = channels_from_results(args.trial)
    elif args.from_base:
        sys.exit("[目标] --from-base 需要配 --trial 或 --channels 指定通道")
    else:
        path = Path(args.student) if args.student else DEFAULT_STUDENT
        tag, chs, student_ck = read_student_ckpt(path)
        cands = [(tag, chs)]
        print(f"学生起点 = {path}  (tag {tag}, 通道 {chs})")

    if args.tag:                                   # 同一配置跑两支起点时用来区分
        cands = [(args.tag, ch) for _t, ch in cands]
        print(f"[tag] 覆盖为 {args.tag}")

    if args.smoke:
        args.epochs, args.seeds, args.limit = 1, 1, 4096
        print(f"[smoke] epochs=1 seeds=1 limit=4096 modes={','.join(args.modes)}")

    # ---- 设备 ----
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cpu":
        torch.set_num_threads(args.threads)

    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(exist_ok=True)

    # ---- teacher（只建一次，冻结）----
    teacher, t_epoch = build_teacher(device, args.teacher)
    print(f"device = {device}")
    print(f"teacher = {P.LOG_DIR / P.CKPT_NAME}  (epoch {t_epoch})")
    print(f"teacher channels {P.channel_tuple(teacher)}  weights {P.weight_bytes(teacher)} B")
    with torch.no_grad():
        out = teacher(torch.randn(*P.INPUT_SHAPE, device=device))
    print(f"teacher forward OK {tuple(out.shape)}")

    loaders = E4.make_loaders(args.limit, args.batch)
    train_loader, val_loader, test_loader = loaders

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    manifest = dict(
        run_id=run_id, teacher=str(P.LOG_DIR / P.CKPT_NAME), teacher_epoch=t_epoch,
        student=(str(Path(args.student).resolve()) if (args.student and student_ck is not None)
                 else ("fresh-prune-from-base" if student_ck is None
                       else str(DEFAULT_STUDENT))),
        student_weights=("loaded-from-ckpt" if student_ck is not None
                         else "fresh-prune-from-base"),
        T=args.T, alpha=args.alpha, epochs=args.epochs, lr=args.lr, seeds=args.seeds,
        modes=args.modes, targets={t: c for t, c in cands},
        note="teacher 冻结 eval+no_grad；kd/ce 共用同一 seed 与同一学生起点",
        versions=dict(python=sys.version.split()[0], torch=torch.__version__,
                      numpy=np.__version__),
        started=datetime.now().isoformat(timespec="seconds"))
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    seeds = [1001 + k for k in range(args.seeds)]
    print(f"\n{len(cands)} 个配置 × {len(args.modes)} 种模式 × {len(seeds)} 个种子 "
          f"= {len(cands) * len(args.modes) * len(seeds)} 次训练，"
          f"每次 {args.epochs} epoch\n")

    # ---- 先量「蒸馏起点」：学生的初始状态 ----
    # 若 --student 给了 ckpt，这一行就是 E4b 那个点练完后的成绩；
    # 若从原模型现场剪枝，这一行就是「剪枝当下的伤」。
    for tag, ch in cands:
        probe = make_student(ch, device, student_ck)
        got = P.channel_tuple(probe)
        mv, mt = P.evaluate_both(probe, val_loader, test_loader, device)
        append_row(csv_path, dict(
            run_id=run_id, ts=datetime.now().isoformat(timespec="seconds"),
            tag=tag, channels="/".join(str(c) for c in got[:6]),
            weight_bytes=P.weight_bytes(probe),
            cycles=E4.arch_cycles(got[:6]), macs=E4.arch_macs(got[:6]),
            proc_passes=E4.arch_proc_passes(got[:6]),
            mode="init", T=args.T, alpha=args.alpha, epochs=0, lr=args.lr, seed=-1,
            auc_val=f"{mv['auc']:.6f}", fpr_val=f"{mv['fpr_at']:.6f}",
            tpr_val=f"{mv['tpr_at']:.6f}", auc_test=f"{mt['auc']:.6f}",
            fpr_test=f"{mt['fpr_at']:.6f}", tpr_test=f"{mt['tpr_at']:.6f}",
            top1_test=f"{mt['top1']:.4f}", seconds="0", ckpt=""))
        print(f"[init] {tag} {got[:6]}  W={P.weight_bytes(probe)}  "
              f"cycles={E4.arch_cycles(got[:6])}  "
              f"val AUC={mv['auc']:.4f} FPR={mv['fpr_at']:.4f}  "
              f"test AUC={mt['auc']:.4f} FPR={mt['fpr_at']:.4f}")
        del probe
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # ---- 主循环 ----
    for tag, ch in cands:
        for mode in args.modes:
            for seed in seeds:
                print(f"\n=== {tag} `{'/'.join(map(str, ch))}` mode={mode} seed={seed} ===")
                torch.manual_seed(seed)
                np.random.seed(seed)
                t0 = time.time()
                student = make_student(ch, device, student_ck)
                got = P.channel_tuple(student)
                train_student(student, teacher, train_loader, device,
                              args.epochs, args.lr, args.T, args.alpha, mode,
                              tag=f"[{tag}/{mode}/s{seed}] ")
                mv, mt = P.evaluate_both(student, val_loader, test_loader, device)
                secs = time.time() - t0

                ckpt_name = f"{tag}_{mode}_s{seed}.pth.tar"
                torch.save(dict(state_dict=student.state_dict(),
                                channels=list(got[:6]), tag=tag, mode=mode, seed=seed,
                                T=args.T, alpha=args.alpha, epochs=args.epochs,
                                lr=args.lr, run_id=run_id,
                                metrics=dict(val=mv, test=mt)),
                           ckpt_dir / ckpt_name)

                append_row(csv_path, dict(
                    run_id=run_id, ts=datetime.now().isoformat(timespec="seconds"),
                    tag=tag, channels="/".join(str(c) for c in got[:6]),
                    weight_bytes=P.weight_bytes(student),
                    cycles=E4.arch_cycles(got[:6]), macs=E4.arch_macs(got[:6]),
                    proc_passes=E4.arch_proc_passes(got[:6]),
                    mode=mode, T=args.T, alpha=args.alpha, epochs=args.epochs,
                    lr=args.lr, seed=seed,
                    auc_val=f"{mv['auc']:.6f}", fpr_val=f"{mv['fpr_at']:.6f}",
                    tpr_val=f"{mv['tpr_at']:.6f}", auc_test=f"{mt['auc']:.6f}",
                    fpr_test=f"{mt['fpr_at']:.6f}", tpr_test=f"{mt['tpr_at']:.6f}",
                    top1_test=f"{mt['top1']:.4f}", seconds=f"{secs:.1f}",
                    ckpt=ckpt_name))

                print(f"  -> val AUC={mv['auc']:.5f} FPR={mv['fpr_at']:.4f} | "
                      f"test AUC={mt['auc']:.5f} FPR={mt['fpr_at']:.4f} "
                      f"TPR@FPR1%={mt['tpr_at']:.4f}  {secs:.0f}s")
                del student
                if device.type == "cuda":
                    torch.cuda.empty_cache()

    # ---- 收尾 ----
    report = format_report(read_rows(csv_path))
    (out_dir / "distill.txt").write_text(report + "\n", encoding="utf-8")
    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + report)
    print(f"\n已写: {csv_path}")
    print(f"已写: {out_dir / 'distill.txt'}")
    print(f"已存: {ckpt_dir}\\*.pth.tar")


if __name__ == "__main__":
    main()
