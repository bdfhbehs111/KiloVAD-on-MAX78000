"""E1c 复核：把 Pareto 前沿的候选用多个 seed 重跑，量出「真差异」vs「seed 噪声」。

为什么需要这一步
================
E1c 的每个 trial 只用了一个 seed（seed = trial.number）。同一个通道配置换一个随机种子，
val 上的 FPR@TPR95 就能差 0.003~0.005（这一点在 E1b 里已经量过：同一模型换 checkpoint
就差 0.0029）。而前沿上相邻两点的差距往往也在 0.003 这个量级 —— 换句话说：

    **Optuna 报出来的顺序，有一部分是噪声顺序。**

所以本脚本对前沿候选各跑 N 个 seed，报 mean / sd / [min,max]。
只有 sd 明显小于两点间差距时，那个排序才算数。

顺带量一件事：E1b 和 E1c 都是 lr=1e-3 + 5 epoch。trial 0（不剪枝、只多训 5 epoch）
的 val 反而从 0.0103 退化到 0.0141，说明 lr=1e-3 对这个已收敛的模型偏大。本脚本支持
--lr 扫描，用来回答「是配置不够好，还是恢复预算不够」。

用法
    python _verify.py                        # 默认取 pareto.json 的前沿，3 个 seed
    python _verify.py --top 6 --seeds 3
    python _verify.py --lr 3e-4 --lr 1e-4    # 顺带扫 lr（每个 lr 都跑满 seeds）
"""

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import torch

BASE_DIR = Path(__file__).resolve().parent


def load_e1c():
    """按文件名加载 optuna.py —— 不能写 `import optuna`，那样会导到 optuna 库自己。"""
    spec = importlib.util.spec_from_file_location("e1c", BASE_DIR / "optuna.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


e1c = load_e1c()
P = e1c.P


def load_candidates(top):
    """取 Pareto 前沿（按 bytes 升序）里等间距的 top 个，再固定加一个不剪枝对照组。

    等间距而不是取最小的 top 个：只取最省内存的那几个，会漏掉"大一点但明显更准"的点，
    而那正是帕累托前沿存在的意义。

    对照组 (64,96,96,64,32,16) = 不剪枝 + 同样 epoch 数。它的作用是把"多训 N 轮"本身的
    影响从剪枝影响里扣掉 —— E1c trial 0 已经显示这个影响不是 0（val 0.0103 -> 0.0141）。
    """
    pj = BASE_DIR / "pareto.json"
    if pj.exists():
        front = json.loads(pj.read_text(encoding="utf-8"))["front"]
        chs = [[f[f"conv{i}"] for i in range(1, 7)] for f in front]
    else:
        rows = e1c.read_rows(BASE_DIR / "results.csv")
        rows = [r for r in rows if r.get("state") == "complete"]
        rows.sort(key=lambda r: e1c._num(r, "weight_bytes"))
        chs = [[int(e1c._num(r, f"ch{i}")) for i in range(1, 7)] for r in rows]

    if len(chs) > top:
        step = len(chs) / top
        chs = [chs[min(int(i * step), len(chs) - 1)] for i in range(top)]

    cands = [(f"m{i}", ch) for i, ch in enumerate(chs)]
    ctrl = list(P.BASE_CHANNELS)
    if ctrl not in chs:
        cands.append(("ctrl-noprune", ctrl))
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, nargs="+", default=[1e-3])
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda", "auto"])
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--out-csv", default="verify.csv")
    ap.add_argument("--out-txt", default="verify.txt")
    ap.add_argument("--pick", type=int, nargs="+", default=None,
                    help="指定 trial 编号（通道从 results.csv 读）；不给就用 pareto.json 前沿")
    ap.add_argument("--no-ctrl", action="store_true", help="不追加不剪枝对照组")
    args = ap.parse_args()

    device = torch.device("cuda" if (args.device == "auto" and torch.cuda.is_available())
                          else (args.device if args.device != "auto" else "cpu"))
    if device.type == "cpu":
        torch.set_num_threads(args.threads)

    loaders = e1c.make_loaders(0, P.BATCH)
    if args.pick:
        rows = {int(e1c._num(r, "trial")): r
                for r in e1c.read_rows(BASE_DIR / "results.csv")}
        cands = [(f"t{t}", [int(e1c._num(rows[t], f"ch{i}")) for i in range(1, 7)])
                 for t in args.pick]
        if not args.no_ctrl and [c for _, c in cands].count(list(P.BASE_CHANNELS)) == 0:
            cands.append(("ctrl-noprune", list(P.BASE_CHANNELS)))
    else:
        cands = load_candidates(args.top)
    print(f"\n复核 {len(cands)} 个候选 × {len(args.lr)} 个 lr × {args.seeds} 个 seed "
          f"= {len(cands) * len(args.lr) * args.seeds} 次训练，device={device}")

    fields = ["tag", "lr", "seed", "ch1", "ch2", "ch3", "ch4", "ch5", "ch6",
              "weight_bytes", "macs", "proc_passes", "fpr_val", "fpr_test",
              "auc_val", "auc_test", "seconds"]
    out_csv = BASE_DIR / args.out_csv
    out_csv.unlink(missing_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=fields).writeheader()

    results = []
    for tag, ch in cands:
        for lr in args.lr:
            vals_v, vals_t, secs = [], [], []
            for k in range(args.seeds):
                seed = 1001 + k
                print(f"  {tag} {ch} lr={lr:g} seed={seed} ...", flush=True)
                _, m = e1c.run_one(ch, args.epochs, lr, seed, device, loaders)
                vals_v.append(m["fpr_val"])
                vals_t.append(m["fpr_test"])
                secs.append(m["seconds"])
                with open(out_csv, "a", newline="", encoding="utf-8") as fh:
                    csv.DictWriter(fh, fieldnames=fields).writerow({
                        "tag": tag, "lr": lr, "seed": seed,
                        **{f"ch{i + 1}": m["channels"][i] for i in range(6)},
                        "weight_bytes": m["weight_bytes"], "macs": m["macs"],
                        "proc_passes": m["proc_passes"],
                        "fpr_val": f"{m['fpr_val']:.6f}", "fpr_test": f"{m['fpr_test']:.6f}",
                        "auc_val": f"{m['auc_val']:.6f}", "auc_test": f"{m['auc_test']:.6f}",
                        "seconds": f"{m['seconds']:.1f}"})
                    fh.flush()
            results.append(dict(tag=tag, ch=ch, lr=lr, bytes=m["weight_bytes"],
                                macs=m["macs"], ps=m["proc_passes"],
                                v_mean=sum(vals_v) / len(vals_v),
                                v_min=min(vals_v), v_max=max(vals_v),
                                t_mean=sum(vals_t) / len(vals_t),
                                t_min=min(vals_t), t_max=max(vals_t),
                                sec=sum(secs) / len(secs)))

    # ---- 出表 ----
    lines = [f"{'tag':10s} {'lr':>7s} {'ch1..ch6':>22s} {'bytes':>7s} {'macs':>9s} {'ps':>3s} "
             f"{'val mean':>9s} {'sd':>7s} {'[min,max]':>17s} "
             f"{'test mean':>10s} {'sd':>7s} {'[min,max]':>17s} {'s':>5s}",
             "-" * 128]
    for r in sorted(results, key=lambda r: r["bytes"]):
        # seeds 少时样本 sd 不稳，用半区间宽度当稳健替代
        vsd = (r["v_max"] - r["v_min"]) / 2
        tsd = (r["t_max"] - r["t_min"]) / 2
        lines.append(
            f"{r['tag']:10s} {r['lr']:7.1e} {'/'.join(str(c) for c in r['ch']):>22s} "
            f"{r['bytes']:7d} {r['macs']:9d} {r['ps']:3d} "
            f"{r['v_mean']:9.4f} {vsd:7.4f} "
            f"{'[%.4f,%.4f]' % (r['v_min'], r['v_max']):>17s} "
            f"{r['t_mean']:10.4f} {tsd:7.4f} "
            f"{'[%.4f,%.4f]' % (r['t_min'], r['t_max']):>17s} "
            f"{r['sec']:5.0f}")
    text = "\n".join(lines)
    print("\n" + text)
    (BASE_DIR / args.out_txt).write_text(
        text + f"\n\n生成: {datetime.now().isoformat(timespec='seconds')}"
        f"  epochs={args.epochs}  seeds={args.seeds}\n", encoding="utf-8")
    print(f"\n已写: {out_csv}")


if __name__ == "__main__":
    main()
