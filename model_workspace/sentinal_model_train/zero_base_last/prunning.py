"""E1b —— 逐层敏感度扫描（为 E1c/Optuna 准备数据）

对 conv1..conv6 中的**每一层单独**剪掉 out-channels 的 25% / 50% / 75%，
短微调恢复，量 FPR@TPR=0.95。其余层保持 100%，所以每个点读出来的是那一层的敏感度。

-----------------------------------------------------------------------------
为什么没有用 torch_pruning 的 DependencyGraph / MagnitudePruner
-----------------------------------------------------------------------------
ai8x.QuantizationAwareModule.forward 里是（ai8x.py:817）：

    x = self._conv_forward(x, self.op.weight, self.op.bias)

而 ai8x.py:725-726 把这行做成了：

    self._conv_forward = op._conv_forward        # 借用 nn.Conv1d 的函数式实现

**nn.Conv1d.forward() 从未被调用**，self.op 只是个权重容器。
torch_pruning 的 tracer 靠 forward hook 记模块（graph.py:460-464），
hook 不触发 → 图里一个卷积都没有 → get_all_groups() 返回 0。
用 `--why-tp` 可以亲手复现这个证据。

打通它还有另外 4 个断点：
  importance.py:202   w = layer.weight.data[idxs]        包装层没有 .weight
  importance.py:342   只认 prune_conv_out_channels 这个函数对象
  graph.py            unwrapped 检测用 m.__class__ in ...（精确类匹配）
  graph.py:302        isinstance(m, (nn._ConvNd, nn.Linear)) 默认 root 类型

而这个模型是纯链式（conv1→conv2→...→conv6→fc，零分支、无残差、无 concat）。
依赖图存在的意义是处理分支拓扑；这里没有分支，所以它带来零收益。
因此本脚本用 **torch_pruning 的同一个重要性判据**（见 channel_importance 的注释）
＋**显式依赖同步**（剪第 k 层输出，必须同步改第 k+1 层输入）。

-----------------------------------------------------------------------------
产出（全部落在 --out 指定的目录里，默认 ./prune_e1b/）
-----------------------------------------------------------------------------
  results.csv      每点一行，**边跑边追加**，中途崩了也不丢
                   列：run_id ts layer ratio_req ratio_actual ch1..ch6 fc_in
                       weight_bytes d_weight_bytes auc fpr_at d_fpr_at tpr_at
                       top1 ft_epochs seed ckpt seconds
                   这组列是直接可以喂 Optuna 的：ch1..ch6 就是搜索空间的取值
  results.txt      对齐的大表，可直接贴报告
  manifest.json    这次跑的元信息（checkpoint / epoch / seed / ft_epochs / lr /
                   round_to / 每层合法取值），Optuna trial 需要能追溯先验来源
  ckpts/*.pth.tar  每个剪枝点剪完 + 微调后的 weights-only checkpoint。
                   **存这个是为了 E1c 的 cycle 目标：以后要对这 18 个点跑 ai8xize，
                   不必重新剪一遍。**

用法
    python prunning.py --why-tp            # 复现 groups=0 的证据，不剪不训
    python prunning.py --smoke             # 门禁：剪 3 次 + 前向 + 数通道
    python prunning.py --ft-epochs 0       # 12 分钟，先看形状（剪枝当下的伤）
    python prunning.py                     # 全量 18 点（约 1.5-2 小时）
    python prunning.py --resume            # 崩了接着跑，自动跳过已完成的点
    python prunning.py --summary           # 不加训练，只把 results.csv 打成表
    python prunning.py --layers conv2 conv3 --ratios 0.5 0.75
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader, Subset

BASE_DIR = Path(__file__).resolve().parent
AI8X_TRAINING_DIR = BASE_DIR / "ai8x-training"
if not AI8X_TRAINING_DIR.is_dir():          # 本文件被挪进 pruning_search_data/ 之后
    AI8X_TRAINING_DIR = BASE_DIR.parent / "ai8x-training"
sys.path.insert(0, str(AI8X_TRAINING_DIR))

import ai8x                                                        # noqa: E402
from datasets.sentinel import sentinel_get_datasets                # noqa: E402
from models.sentinel import KiloVAD_MAX                            # noqa: E402

# simulate=False -> 纯 float，量化模块直通。和基线训练、auc_check.py 同口径，
# 所以 0.9962 / 1.18% 可以直接当参照。
ai8x.set_device(85, simulate=False, round_avg=False)

LOG_DIR = AI8X_TRAINING_DIR / "logs" / "zero_base___2026.10.31-170625"
CKPT_NAME = "zero_base_best.pth.tar"

INPUT_SHAPE = (1, 128, 128)
BATCH = 64
ROUND_TO = 4
CHAIN = ["conv1", "conv2", "conv3", "conv4", "conv5", "conv6", "fc"]
PRUNABLE = ["conv1", "conv2", "conv3", "conv4", "conv5", "conv6"]   # fc 只有 2 类，不剪
DEFAULT_RATIOS = [0.25, 0.50, 0.75]
TARGET_TPR, TARGET_FPR = 0.95, 0.01
BASE_CHANNELS = (64, 96, 96, 64, 32, 16)

FIELDS = [
    "run_id", "ts", "layer", "ratio_req", "ratio_actual",
    "ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "fc_in",
    "weight_bytes", "d_weight_bytes",
    "auc", "fpr_at", "d_fpr_at", "tpr_at", "top1",
    "ft_epochs", "seed", "ckpt", "seconds",
]


# --------------------------------------------------------------------------- #
# 模型
# --------------------------------------------------------------------------- #
def build_model(device):
    ckpt = torch.load(LOG_DIR / CKPT_NAME, map_location="cpu", weights_only=False)
    model = KiloVAD_MAX(
        channels=BASE_CHANNELS,
        num_classes=2,
        num_channels=128,
        bias="conv1.op.bias" in ckpt["state_dict"],
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model.to(device), ckpt.get("epoch")


def weight_bytes(model):
    """和 train.py 日志的 'Params' 同口径：只数 2/3/4 维张量 = int8 权重字节数。
    不含 bias，也不含 ai8x 每层 9 个量化标量。"""
    return sum(v.numel() for v in model.state_dict().values() if v.dim() in (2, 3, 4))


def channel_tuple(model):
    """(ch1..ch6, fc_in)。纯链式 + 依赖同步下 fc_in 必然等于 ch6，留着当自检。"""
    out = [getattr(model, n).op.out_channels for n in PRUNABLE]
    out.append(model.fc.op.in_features)
    return tuple(out)


# --------------------------------------------------------------------------- #
# 重要性 + 剪枝
# --------------------------------------------------------------------------- #
def channel_importance(weight):
    """每个输出通道的 L2 范数。

    这就是 torch_pruning 的判据本身。对照 importance.py:202：
        w = layer.weight.data[idxs].flatten(1)
        local_imp = w.abs().pow(self.p)          # p=2
        group_reduction='mean'  -> 对通道内取均值
    所以它是 sqrt(mean(w^2)) = RMS；和 L2 只差一个正的常数因子，**排序完全相同**。
    这个模型没有 BatchNorm，拿不到 gamma，L2 就是能用的最强准则。
    """
    return weight.reshape(weight.shape[0], -1).norm(p=2, dim=1)


def keep_index(weight, ratio, round_to=ROUND_TO):
    """返回要保留的通道下标（升序）。

    round_to 对齐：保留数必须落在 round_to 的倍数上，
    否则 MAX78000 packing 时会补零浪费 word（load.py:236-246 合法但浪费）。
    """
    out_c = weight.shape[0]
    keep_n = out_c - int(round(out_c * ratio))
    keep_n = max(round_to, (keep_n // round_to) * round_to)
    if keep_n >= out_c:
        return torch.arange(out_c)
    imp = channel_importance(weight)
    return torch.sort(torch.topk(imp, keep_n).indices).values


def _slice_out(op, keep):
    op.weight = nn.Parameter(op.weight.data.index_select(0, keep).clone())
    if op.bias is not None:
        op.bias = nn.Parameter(op.bias.data.index_select(0, keep).clone())
    if hasattr(op, "out_channels"):        # conv
        op.out_channels = int(keep.numel())
    else:                                  # linear
        op.out_features = int(keep.numel())


def _slice_in(op, keep):
    # conv weight (out, in, k) 和 linear weight (out, in) 的输入维都是 1
    op.weight = nn.Parameter(op.weight.data.index_select(1, keep).clone())
    if hasattr(op, "in_channels"):         # conv
        op.in_channels = int(keep.numel())
    else:                                  # linear
        op.in_features = int(keep.numel())


def prune_layer(model, layer_name, ratio):
    """剪一层，并同步下游。

    这是整个 E1b 唯一的真工程点：剪 conv_k 的输出通道会让 conv_{k+1}
    的输入通道对不上。纯链式拓扑下，同步规则就一条：
        剪 conv_k 的 out  ->  必须同时剪 conv_{k+1} 的 in（fc 同理，改 in_features）
    """
    idx = CHAIN.index(layer_name)
    if idx == len(CHAIN) - 1:
        raise ValueError(f"{layer_name} 后面没有下游层，剪它的输出没有意义")

    layer = getattr(model, layer_name)
    keep = keep_index(layer.op.weight.data, ratio)
    _slice_out(layer.op, keep)
    _slice_in(getattr(model, CHAIN[idx + 1]).op, keep)
    return keep


# --------------------------------------------------------------------------- #
# 评估 / 训练
# --------------------------------------------------------------------------- #
def pick_points(fpr, tpr):
    """满足约束里最严的那个点（不是离目标最近的点）。"""
    ok = tpr >= TARGET_TPR
    fpr_at = float(fpr[ok].min()) if ok.any() else float("nan")
    ok = fpr <= TARGET_FPR
    tpr_at = float(tpr[ok].max()) if ok.any() else float("nan")
    return fpr_at, tpr_at


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    logits_all, labels_all = [], []
    for inputs, labels in loader:
        logits_all.append(model(inputs.to(device)).cpu())
        labels_all.append(labels)
    logits = torch.cat(logits_all).numpy()
    labels = torch.cat(labels_all).numpy()

    # 关键：没有 softmax 的网络，人声得分必须是 log-odds = logit1 - logit0。
    # 裸 logit1 会算出 AUC 0.34（详见 auc_check.py 里的注释）。
    scores = logits[:, 1] - logits[:, 0]
    top1 = (logits.argmax(axis=1) == labels).mean() * 100
    auc = roc_auc_score(labels, scores)
    fpr, tpr, _ = roc_curve(labels, scores)
    fpr_at, tpr_at = pick_points(fpr, tpr)
    return dict(top1=top1, auc=auc, fpr_at=fpr_at, tpr_at=tpr_at)


def finetune(model, loader, device, epochs, lr):
    """剪枝后短微调恢复。沿用基线配方：Adam 常数 lr + CrossEntropy。"""
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    for epoch in range(epochs):
        t0 = time.time()
        total = correct = 0
        loss_sum = 0.0
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            out = model(inputs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * labels.size(0)
            correct += (out.argmax(1) == labels).sum().item()
            total += labels.size(0)
        print(f"      ft[{epoch + 1}/{epochs}]  loss={loss_sum / total:.4f}  "
              f"top1={100 * correct / total:6.2f}%  {time.time() - t0:5.1f}s")
    model.eval()


# --------------------------------------------------------------------------- #
# CSV：边跑边追加，支持 resume
# --------------------------------------------------------------------------- #
def read_rows(csv_path):
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_row(csv_path, row):
    """立刻落盘 + flush。18 点的活不能等到最后才写。"""
    new_file = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDS})
        f.flush()
    # 同步刷新可读表格：进程被硬杀（TerminateProcess）时也不会只剩一个 CSV
    txt_path = csv_path.with_name("results.txt")
    txt_path.write_text(format_table(read_rows(csv_path)) + "\n", encoding="utf-8")


def format_table(rows):
    """把 CSV 行打成对齐的表。返回文本，调用方决定打印还是落盘。"""
    if not rows:
        return "没有数据。"
    base = next((r for r in rows if r["layer"] == "baseline"), None)
    base_fpr = float(base["fpr_at"]) if base else float("nan")
    base_w = int(base["weight_bytes"]) if base else 0

    lines = [f"{'layer':9s} {'req':>5s} {'ch1..ch6 (fc_in)':>30s} "
             f"{'weights_B':>10s} {'dW':>8s} {'AUC':>8s} {'FPR@TPR95':>10s} "
             f"{'dFPR':>8s} {'TPR@FPR1%':>10s} {'sec':>5s}",
             "-" * 122]
    for r in rows:
        ch = "/".join(r[f"ch{i}"] for i in range(1, 7))
        line = (f"{r['layer']:9s} {float(r['ratio_req']):5.2f} "
                f"{ch + ' (' + r['fc_in'] + ')':>30s} {int(r['weight_bytes']):10d}")
        if r["layer"] == "baseline":
            line += f" {'—':>8s} {float(r['auc']):8.4f} {float(r['fpr_at']):10.4f} {'—':>8s}"
        else:
            line += (f" {int(r['weight_bytes']) - base_w:+8d} {float(r['auc']):8.4f} "
                     f"{float(r['fpr_at']):10.4f} {float(r['fpr_at']) - base_fpr:+8.4f}")
        line += f" {float(r['tpr_at']):10.4f} {float(r['seconds']):5.0f}"
        lines.append(line)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 诊断：复现 torch_pruning 在 ai8x 上失效的证据
# --------------------------------------------------------------------------- #
def why_torch_pruning_fails(model, example_inputs):
    import torch_pruning as tp

    print("\n[诊断] 为什么 torch_pruning 在这里拿不到 pruning group")
    fired = {"op": 0, "wrapper": 0}

    hs = [model.conv1.op.register_forward_hook(lambda *_: fired.__setitem__("op", fired["op"] + 1)),
          model.conv1.register_forward_hook(lambda *_: fired.__setitem__("wrapper", fired["wrapper"] + 1))]
    model(example_inputs)
    for h in hs:
        h.remove()
    print(f"  conv1.op 的 forward hook 触发次数 : {fired['op']}   <- 0 就是根因")
    print(f"  conv1（包装层）的 hook 触发次数  : {fired['wrapper']}")

    dg = tp.DependencyGraph()
    dg.build_dependency(model, example_inputs, verbose=False)
    from collections import Counter
    hist = Counter(type(m).__name__ for m in dg.module2node.keys())
    print(f"  module2node 里的模块类型分布     : {dict(hist)}")
    conv_seen = [m for m in dg.module2node if isinstance(m, nn.modules.conv._ConvNd)]
    print(f"  图中被识别出的 nn.Conv1d 数量    : {len(conv_seen)}   <- 0 就是根因")
    print(f"  get_all_groups() 分组数          : {len(list(dg.get_all_groups()))}")
    print("\n  结论：ai8x.py:817 用 self._conv_forward(self.op.weight, ...) 而不是"
          " self.op(x)，\n  nn.Conv1d.forward 从未被调用，hook 不触发，依赖图为空。")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", nargs="+", default=PRUNABLE, choices=PRUNABLE)
    ap.add_argument("--ratios", nargs="+", type=float, default=DEFAULT_RATIOS)
    ap.add_argument("--ft-epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--out", default="prune_e1b", help="产出目录")
    ap.add_argument("--resume", action="store_true", help="跳过 CSV 里已完成 (层,比例)")
    ap.add_argument("--summary", action="store_true", help="只读 CSV 出表，不训练")
    ap.add_argument("--why-tp", action="store_true", help="复现 torch_pruning 失效的证据")
    ap.add_argument("--smoke", action="store_true", help="门禁：剪 3 次 + 前向 + 数通道")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cpu", choices=["auto", "cpu", "cuda"],
                    help="默认 cpu：把 GPU 整个让给前台程序。瓶颈在 DataLoader 不在算力，"
                         "CPU 每 epoch 28.8s vs GPU 11.3s，而实测瓶颈是 53s/epoch 的数据加载")
    ap.add_argument("--threads", type=int, default=12,
                    help="CPU 线程数。32 逻辑核里只用 12，剩下 20 个留给前台程序")
    args = ap.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    out_dir = BASE_DIR / args.out
    csv_path = out_dir / "results.csv"
    txt_path = out_dir / "results.txt"
    man_path = out_dir / "manifest.json"
    ckpt_dir = out_dir / "ckpts"

    if args.summary:
        print(format_table(read_rows(csv_path)))
        return

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cpu":
        torch.set_num_threads(args.threads)
        print(f"device = cpu   torch threads = {args.threads}   （GPU 未使用）")
    else:
        print(f"device = {device}")

    example_inputs = torch.randn(*INPUT_SHAPE, device=device)
    model0, epoch = build_model(device)
    with torch.no_grad():
        out = model0(example_inputs)
    print(f"checkpoint {CKPT_NAME} (epoch {epoch})  forward OK {tuple(out.shape)}")
    print(f"baseline channels {channel_tuple(model0)}  weights {weight_bytes(model0)} B")

    if args.why_tp:
        why_torch_pruning_fails(model0, example_inputs)
        return

    if args.smoke:
        for layer, ratio in [("conv3", 0.5), ("conv6", 0.5), ("conv1", 0.75)]:
            m, _ = build_model(device)
            keep = prune_layer(m, layer, ratio)
            with torch.no_grad():
                o = m(example_inputs)
            print(f"  smoke {layer} @ {ratio:.0%}: 保留 {keep.numel()} 通道  "
                  f"out {tuple(o.shape)}  channels {channel_tuple(m)}  "
                  f"weights {weight_bytes(m)} B")
        print("\n门禁通过 -> 可以跑全量。")
        return

    # ---------------- 产出目录 + manifest ----------------
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    manifest = {
        "run_id": run_id,
        "checkpoint": str(LOG_DIR / CKPT_NAME),
        "checkpoint_epoch": epoch,
        "base_channels": list(BASE_CHANNELS),
        "input_shape": list(INPUT_SHAPE),
        "batch": BATCH,
        "round_to": ROUND_TO,
        "ft_epochs": args.ft_epochs,
        "lr": args.lr,
        "seed": args.seed,
        "shebang": "逐层敏感度扫描，为 E1c/Optuna 提供先验",
        # Optuna 搜索空间：每层合法取值 = round_to 的倍数，[4, 原始通道数]
        "search_space": {
            f"conv{i + 1}": {
                "original": BASE_CHANNELS[i],
                "allowed": list(range(ROUND_TO, BASE_CHANNELS[i] + 1, ROUND_TO)),
            } for i in range(6)
        },
        "note": "fc 只有 2 类，不可剪；剪 conv_k 的 out 会同步切 conv_{k+1} 的 in",
        "started": datetime.now().isoformat(timespec="seconds"),
    }
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"产出目录 {out_dir}")

    # ---------------- 数据（只加载一次） ----------------
    print("\n加载数据集 ...")
    train_ds, test_ds = sentinel_get_datasets(data=None, load_train=True, load_test=True)
    n_train = train_ds.valid_indices.start      # valid 段排在后面，只取训练部分
    train_loader = DataLoader(Subset(train_ds, range(n_train)), batch_size=BATCH,
                              shuffle=True, num_workers=0, drop_last=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False, num_workers=0)
    print(f"微调 train {n_train} 条 / 评估 test {len(test_ds)} 条")

    done = set()
    if args.resume:
        for r in read_rows(csv_path):
            if r["layer"] == "baseline":
                done.add(("baseline", 0.0))
            else:
                done.add((r["layer"], round(float(r["ratio_req"]), 4)))
        print(f"[resume] CSV 里已有 {len(done)} 条，将跳过")

    def make_row(tag_layer, ratio_req, model, metrics, secs, ckpt=None):
        ch = channel_tuple(model)
        ratio_actual = 1.0 - (ch[PRUNABLE.index(tag_layer)] / BASE_CHANNELS[PRUNABLE.index(tag_layer)]) \
            if tag_layer in PRUNABLE else 0.0
        return dict(
            run_id=run_id, ts=datetime.now().isoformat(timespec="seconds"),
            layer=tag_layer, ratio_req=f"{ratio_req:.4f}",
            ratio_actual=f"{ratio_actual:.4f}",
            **{f"ch{i + 1}": ch[i] for i in range(6)}, fc_in=ch[6],
            weight_bytes=weight_bytes(model),
            auc=f"{metrics['auc']:.6f}", fpr_at=f"{metrics['fpr_at']:.6f}",
            tpr_at=f"{metrics['tpr_at']:.6f}", top1=f"{metrics['top1']:.4f}",
            ft_epochs=args.ft_epochs, seed=args.seed,
            ckpt=str(ckpt) if ckpt else "", seconds=f"{secs:.1f}",
        )

    # ---------------- baseline ----------------
    if ("baseline", 0.0) in done:
        print("\n[baseline] 已在 CSV 中，跳过")
    else:
        print("\n[baseline] 不剪、不微调")
        t0 = time.time()
        met = evaluate(model0, test_loader, device)
        row = make_row("baseline", 0.0, model0, met, time.time() - t0)
        row["d_weight_bytes"], row["d_fpr_at"] = 0, "0.000000"
        append_row(csv_path, row)
        print(f"  AUC={met['auc']:.4f}  FPR@TPR95={met['fpr_at']:.4f}  "
              f"TPR@FPR1%={met['tpr_at']:.4f}  weights={weight_bytes(model0)} B")
    del model0

    base_row = next(r for r in read_rows(csv_path) if r["layer"] == "baseline")
    base_w, base_fpr = int(base_row["weight_bytes"]), float(base_row["fpr_at"])

    # ---------------- 逐点 ----------------
    points = [(ly, r) for ly in args.layers for r in args.ratios]
    todo = [(ly, r) for ly, r in points if (ly, round(r, 4)) not in done]
    print(f"\n共 {len(points)} 个点，本次要做 {len(todo)} 个，每点微调 {args.ft_epochs} epoch\n")

    for i, (layer, ratio) in enumerate(todo, 1):
        print(f"=== [{i}/{len(todo)}] {layer} @ {ratio:.0%} ===")
        t0 = time.time()

        model, _ = build_model(device)
        prune_layer(model, layer, ratio)
        print(f"     剪完 channels {channel_tuple(model)}  weights={weight_bytes(model)} B")

        if args.ft_epochs > 0:
            finetune(model, train_loader, device, args.ft_epochs, args.lr)

        met = evaluate(model, test_loader, device)
        secs = time.time() - t0

        # 存剪完 + 微调后的权重，供 E1c 补 cycle（跑 ai8xize）用
        ckpt_path = ckpt_dir / f"{layer}_r{ratio:.3f}.pth.tar"
        torch.save({
            "state_dict": model.state_dict(),
            "channels": list(channel_tuple(model)[:6]),
            "layer": layer, "ratio_req": ratio,
            "metrics": met, "run_id": run_id,
        }, ckpt_path)

        row = make_row(layer, ratio, model, met, secs, ckpt_path.name)
        row["d_weight_bytes"] = weight_bytes(model) - base_w
        row["d_fpr_at"] = f"{met['fpr_at'] - base_fpr:.6f}"
        append_row(csv_path, row)                                  # 边跑边落盘

        print(f"  -> AUC={met['auc']:.4f}  FPR@TPR95={met['fpr_at']:.4f}  "
              f"TPR@FPR1%={met['tpr_at']:.4f}   {secs:.0f}s")

        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # ---------------- 收尾 ----------------
    rows = read_rows(csv_path)
    table = format_table(rows)
    print("\n" + table)
    txt_path.write_text(table + "\n", encoding="utf-8")

    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    manifest["n_points_done"] = len(rows)
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n已写: {csv_path}")
    print(f"已写: {txt_path}")
    print(f"已写: {man_path}")
    print(f"已存: {ckpt_dir}\\*.pth.tar  ({len(list(ckpt_dir.glob('*.pth.tar')))} 个)")


if __name__ == "__main__":
    main()
