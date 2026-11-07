"""E1 —— 幅度侧信道探针（不训练）

问题：这个模型判断"人声/非人声"时，是不是在偷偷用**音量**当捷径？
      （训练数据里 Mobvoi 唤醒词和 ESC-50 的录音电平本来就不一样）

方法：把 test 集波形乘上增益 g ∈ {1/16, 1/8, 1/4, 1/2, 1, 2, 4}，
      g=1 是原样，g<1 模拟"更安静"，g>1 模拟"更响"（带 int8 截断）。
      对每个 g 测 FPR@TPR=0.95 / TPR@FPR=1% / AUC / Top1。

判据：
  * 如果曲线在 g ∈ [0.25, 4] 基本平坦（ΔFPR < 0.003，即 test 上的噪声地板），
    说明模型对音量不敏感 -> 逐带归一化（E2）可以省。
  * 如果低增益下 FPR 暴涨（安静时误报猛增），说明模型在靠音量判断 -> E2 必做。

自检：g=1.0 必须复现基线 FPR@TPR95=0.011809 / AUC=0.996197 / Top1=97.5978，
      否则说明缩放或评估口径出了问题。

输入数据是 int8 折叠波形（[−128,127]），dataset 把它当 float 直接给模型。
所以增益 g 就是在这个整数刻度上乘：x' = clip(round(x·g), −128, 127)。
这是"同一段录音在更低/更高电平下重新过 int8 量化"的正确模拟。
"""

import csv
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader

BASE_DIR = Path(__file__).resolve().parent
AI8X_TRAINING_DIR = BASE_DIR / "ai8x-training"
sys.path.insert(0, str(AI8X_TRAINING_DIR))

import ai8x                                                     # noqa: E402
from models.sentinel import KiloVAD_MAX                         # noqa: E402
from datasets.sentinel import sentinel_get_datasets             # noqa: E402

ai8x.set_device(85, simulate=False, round_avg=False)

LOG_DIR = AI8X_TRAINING_DIR / "logs" / "zero_base___2026.10.31-170625"
CKPT = "zero_base_best.pth.tar"
BATCH = 64
GAINS = [0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0]
TARGET_TPR, TARGET_FPR = 0.95, 0.01


def pick_points(fpr, tpr):
    ok = tpr >= TARGET_TPR
    fpr_at = float(fpr[ok].min()) if ok.any() else float("nan")
    ok = fpr <= TARGET_FPR
    tpr_at = float(tpr[ok].max()) if ok.any() else float("nan")
    return fpr_at, tpr_at


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device = {device}")

    ckpt = torch.load(LOG_DIR / CKPT, map_location="cpu", weights_only=False)
    use_bias = "conv1.op.bias" in ckpt["state_dict"]
    model = KiloVAD_MAX(channels=(64, 96, 96, 64, 32, 16), num_classes=2,
                        num_channels=128, bias=use_bias)
    model.load_state_dict(ckpt["state_dict"])
    model.eval().to(device)
    print(f"checkpoint {CKPT}  epoch={ckpt.get('epoch')}  bias={use_bias}")

    _, test_ds = sentinel_get_datasets(data=None, load_train=False, load_test=True)
    labels_true = test_ds.targets
    print(f"test {len(test_ds)} 条 (pos {int(labels_true.sum())}, "
          f"neg {int((1 - labels_true).sum())})")

    loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False, num_workers=0)

    rows = []
    for g in GAINS:
        logits_all, labels_all = [], []
        with torch.no_grad():
            for inputs, labels in loader:
                x = torch.clamp(torch.round(inputs.to(device) * g), -128, 127)
                logits_all.append(model(x).cpu())
                labels_all.append(labels)
        logits = torch.cat(logits_all).numpy()
        labels = torch.cat(labels_all).numpy()

        scores = logits[:, 1] - logits[:, 0]          # log-odds，决策边界在 0
        top1 = (logits.argmax(axis=1) == labels).mean() * 100
        auc = roc_auc_score(labels, scores)
        fpr, tpr, _ = roc_curve(labels, scores)
        fpr_at, tpr_at = pick_points(fpr, tpr)

        rows.append(dict(gain=g, auc=auc, fpr_at=fpr_at, tpr_at=tpr_at, top1=top1))

    # 基线自检
    base = rows[GAINS.index(1.0)]
    ok = (abs(base["fpr_at"] - 0.011809) < 1e-6
          and abs(base["auc"] - 0.996197) < 1e-6
          and abs(base["top1"] - 97.5978) < 1e-3)
    print("\n[自检 g=1.0] FPR@TPR95=%.6f  AUC=%.6f  Top1=%.4f  -> %s"
          % (base["fpr_at"], base["auc"], base["top1"],
             "复现基线 ✔" if ok else "**与基线不一致，先查**"))

    # 表
    head = f"{'gain':>7s} {'AUC':>9s} {'FPR@TPR95':>11s} {'ΔFPR':>9s} {'TPR@FPR1%':>11s} {'Top1%':>8s}"
    lines = [head, "-" * len(head)]
    base_fpr = base["fpr_at"]
    for r in rows:
        lines.append(f"{r['gain']:7.3f} {r['auc']:9.5f} {r['fpr_at']:11.5f} "
                     f"{r['fpr_at'] - base_fpr:+9.5f} {r['tpr_at']:11.5f} {r['top1']:8.3f}")
    lines += ["",
              "ΔFPR = 相对 g=1.0 的 FPR@TPR95 变化。噪声地板 ≈ 0.003（test 集），",
              "|ΔFPR| < 0.003 视为'对音量不敏感'。"]
    table = "\n".join(lines)
    print("\n" + table)

    csv_path = BASE_DIR / "amplitude_probe.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["gain", "auc", "fpr_at", "tpr_at", "top1"])
        w.writeheader()
        w.writerows(rows)
    (BASE_DIR / "amplitude_probe.txt").write_text(table + "\n", encoding="utf-8")
    print(f"\n已写: {csv_path}")
    print(f"已写: {BASE_DIR / 'amplitude_probe.txt'}")


if __name__ == "__main__":
    main()
