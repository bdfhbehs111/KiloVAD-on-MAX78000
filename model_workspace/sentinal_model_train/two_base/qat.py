"""E6 —— two_base：剪枝 + 自蒸馏模型（t7, 32/24/32/16/8/16）的 ShiftQAT

======================================================================================
起点 / 配方 / 为什么这样写
======================================================================================
    起点 = one_base_distill/ckpts/t7_kd_s1001.pth.tar
           （float，val AUC 0.99536 / test AUC 0.99562 / 10,784 B / 38,016 cycles）

    配方与 ai8x-training/train.py 的 QAT 分支**逐行同序**（train.py:606-630）：
        ai8x.fuse_bn_layers(model)
        ai8x.pre_qat(model, train_loader, args, policy)     # init_hist → stat_collect
                                                            # → init_threshold → apply_scales
        ai8x.initiate_qat(model, policy)                    # weight_bits=8
        然后 Adam(lr=1e-3, wd=1e-4) 训练

    为什么不直接跑 train.py：train.py 的模型工厂拿不到 `channels=(32,24,32,16,8,16)`，
    剪枝后的形状必须显式给。本脚本只替换"怎么建模型"这一件事，QAT 的每一步都调
    ai8x 的原函数，不自己实现任何量化逻辑。

    **这个流程就是 ShiftQAT**：output_shift 由权重量化推导（init_module 里
    shift_quantile=1.0），adjust_output_shift 保持 0、从不参与训练。真正的激活侧
    标定留给后面的 quantize.py --clip-method SCALE（0.85·max）。

======================================================================================
产出
======================================================================================
    two_base_qat_best.pth.tar    val top1 最好的那个 epoch（喂 quantize.py）
    two_base_qat_last.pth.tar    最后一个 epoch
    qat_log.csv                  每个 epoch 的 loss / top1 / AUC / FPR

用法
    python qat.py                  # 默认 10 epoch
    python qat.py --epochs 15 --lr 5e-4
    python qat.py --ckpt <别的.pth.tar>
"""

import argparse
import csv
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
MODEL_DIR = BASE_DIR.parent
TRAIN_DIR = MODEL_DIR / "ai8x-training"
sys.path.insert(0, str(TRAIN_DIR))

import ai8x                                                           # noqa: E402
from datasets.sentinel import sentinel_get_datasets                   # noqa: E402
from models.sentinel import KiloVAD_MAX                               # noqa: E402
import parse_qat_yaml                                                 # noqa: E402

DEFAULT_CKPT = MODEL_DIR / "one_base_distill" / "ckpts" / "t7_kd_s1001.pth.tar"
QAT_POLICY = TRAIN_DIR / "policies" / "qat_policy.yaml"
BATCH = 64
TARGET_TPR = 0.95


# --------------------------------------------------------------------------- #
# 评估：AUC / FPR@TPR=0.95（人声得分 = logit1 - logit0，与全项目同口径）
# --------------------------------------------------------------------------- #
@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    logits_all, labels_all = [], []
    for inputs, labels in loader:
        logits_all.append(model(inputs.to(device)).cpu())
        labels_all.append(labels)
    logits = torch.cat(logits_all).numpy()
    labels = torch.cat(labels_all).numpy()
    scores = logits[:, 1] - logits[:, 0]
    top1 = (logits.argmax(axis=1) == labels).mean() * 100
    auc = roc_auc_score(labels, scores)
    fpr, tpr, _ = roc_curve(labels, scores)
    ok = tpr >= TARGET_TPR
    fpr_at = float(fpr[ok].min()) if ok.any() else float("nan")
    return dict(top1=top1, auc=auc, fpr_at=fpr_at)


def main():
    ap = argparse.ArgumentParser(description="two_base ShiftQAT",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--ckpt", default=str(DEFAULT_CKPT), help="float 起点（剪枝+蒸馏后的学生）")
    ap.add_argument("--epochs", type=int, default=10, help="QAT epoch 数（对齐 train.py: ep30->ep45）")
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--device", default="cuda", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="调试用：等间距抽样")
    ap.add_argument("--smoke", action="store_true", help="门禁：只做 pre_qat+initiate_qat+前向")
    args = ap.parse_args()

    ckpt_path = Path(args.ckpt).resolve()
    if not ckpt_path.is_file():
        sys.exit(f"[ckpt] 找不到 {ckpt_path}")

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cpu":
        torch.set_num_threads(args.threads)

    ai8x.set_device(85, simulate=False, round_avg=False)

    # ---- 建剪枝形状的模型并载入 float 权重 ----
    ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    channels = tuple(int(c) for c in ck["channels"])
    model = KiloVAD_MAX(channels=channels, num_classes=2, num_channels=128,
                        dimensions=(128, 1), bias=True)
    model.load_state_dict(ck["state_dict"])
    model.to(device)
    ai8x.update_model(model)
    n_weights = sum(v.numel() for v in model.state_dict().values() if v.dim() in (2, 3, 4))
    print(f"起点   {ckpt_path.name}  channels={channels}  int8 权重 {n_weights} B")

    # ---- 数据 ----
    train_ds, test_ds = sentinel_get_datasets(data=None, load_train=True, load_test=True)
    n_train = train_ds.valid_indices.start
    tr_idx = list(range(n_train))
    va_idx = list(train_ds.valid_indices)
    te_idx = list(range(len(test_ds)))

    def stride(idx, n):
        return idx if not n else idx[::max(1, len(idx) // n)][:n]

    if args.limit:
        tr_idx = stride(tr_idx, args.limit)
        va_idx = stride(va_idx, args.limit)
        te_idx = stride(te_idx, args.limit)

    train_loader = DataLoader(Subset(train_ds, tr_idx), batch_size=args.batch,
                              shuffle=True, num_workers=0, drop_last=True)
    val_loader = DataLoader(Subset(train_ds, va_idx), batch_size=args.batch,
                            shuffle=False, num_workers=0)
    test_loader = DataLoader(Subset(test_ds, te_idx), batch_size=args.batch,
                             shuffle=False, num_workers=0)
    print(f"train {len(tr_idx)} / val {len(va_idx)} / test {len(te_idx)}")

    # ---- float 参照（量化前的同一模型，同口径）----
    if not args.smoke:
        fv = evaluate(model, val_loader, device)
        ft = evaluate(model, test_loader, device)
        print(f"[float] val AUC={fv['auc']:.5f} FPR@TPR95={fv['fpr_at']:.4f} | "
              f"test AUC={ft['auc']:.5f} FPR@TPR95={ft['fpr_at']:.4f}")

    # ---- QAT：与 train.py 逐行同序 ----
    policy = parse_qat_yaml.parse(str(QAT_POLICY))
    policy["start_epoch"] = 0                       # 本脚本自己就是 QAT 阶段
    print(f"QAT policy: {policy}")
    model.train()
    ai8x.fuse_bn_layers(model)
    print("pre_qat: 收集激活直方图 ...")
    t0 = time.time()
    ai8x.pre_qat(model, train_loader, argparse.Namespace(device=device), policy)
    print(f"pre_qat 完成 {time.time() - t0:.0f}s")
    ai8x.initiate_qat(model, policy)
    model.to(device)
    print("initiate_qat 完成（weight_bits=8）")

    if args.smoke:
        with torch.no_grad():
            out = model(torch.randn(1, 128, 128, device=device))
        print("smoke: forward OK", tuple(out.shape))
        for m in ["conv1", "conv2", "conv3", "conv4", "conv5", "conv6", "fc"]:
            mod = getattr(model, m)
            print(f"  {m:6s} shift={mod.output_shift.item():6.2f}  "
                  f"w=[{mod.op.weight.min():4.0f},{mod.op.weight.max():4.0f}]  "
                  f"thr={mod.activation_threshold.item():.2f}")
        return

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    log_csv = BASE_DIR / "qat_log.csv"
    fields = ["epoch", "ts", "loss", "top1_train", "auc_val", "fpr_val", "top1_val",
              "auc_test", "fpr_test", "seconds", "best"]
    with open(log_csv, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fields).writeheader()

    best_top1, best_path = -1.0, BASE_DIR / "two_base_qat_best.pth.tar"

    def save(path, epoch, best):
        torch.save(dict(
            epoch=epoch, state_dict=model.state_dict(), arch="kilovad_max",
            optimizer_state_dict=None, optimizer_type=None, compression_sched={},
            extras=dict(best_top1=best, best_epoch=epoch, channels=list(channels),
                        qat_policy=str(QAT_POLICY), source=str(ckpt_path)),
        ), path)

    for ep in range(1, args.epochs + 1):
        t0 = time.time()
        model.train()
        loss_sum = correct = total = 0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            out = model(inputs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach()) * labels.size(0)
            correct += (out.argmax(1) == labels).sum().item()
            total += labels.size(0)
        mv = evaluate(model, val_loader, device)
        mt = evaluate(model, test_loader, device)
        secs = time.time() - t0
        best = mv["top1"] > best_top1
        if best:
            best_top1 = mv["top1"]
            save(best_path, ep, best_top1)
        with open(log_csv, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fields).writerow(dict(
                epoch=ep, ts=datetime.now().isoformat(timespec="seconds"),
                loss=f"{loss_sum / total:.5f}", top1_train=f"{100 * correct / total:.4f}",
                auc_val=f"{mv['auc']:.6f}", fpr_val=f"{mv['fpr_at']:.6f}",
                top1_val=f"{mv['top1']:.4f}",
                auc_test=f"{mt['auc']:.6f}", fpr_test=f"{mt['fpr_at']:.6f}",
                seconds=f"{secs:.1f}", best=int(best)))
        print(f"  ep[{ep}/{args.epochs}] loss={loss_sum / total:.4f} "
              f"train_top1={100 * correct / total:6.2f}%  "
              f"val AUC={mv['auc']:.5f} FPR={mv['fpr_at']:.4f} top1={mv['top1']:.2f}%  "
              f"test AUC={mt['auc']:.5f} FPR={mt['fpr_at']:.4f}  "
              f"{secs:5.0f}s" + ("  *best" if best else ""), flush=True)

    save(BASE_DIR / "two_base_qat_last.pth.tar", args.epochs, best_top1)
    print(f"\n已存 {best_path}")
    print(f"已存 {BASE_DIR / 'two_base_qat_last.pth.tar'}")
    print(f"best val top1 = {best_top1:.2f}%")


if __name__ == "__main__":
    main()
