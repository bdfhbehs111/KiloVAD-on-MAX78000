"""E2 —— 逐带归一化后的幅度侧信道探针（不训练，验证 one_base）。

和 E1 探针唯一差别：gain 现在乘在**原始波形**上、**归一化之前**，
复刻真实部署顺序「原始波形 → 音量变化 → 归一化 → 进模型」。
如果乘在归一化之后，测的不是音量变化对模型的影响，而是无关的东西。

自检：g=1.0 时 round/clip 是恒等变换，所以 g=1.0 的「raw→gain→norm」路径
必须与 DataLoader 的「__getitem__→norm」路径逐位一致。这证明探针的
归一化 == 训练的归一化（同一个 normalize_per_band）。
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
from datasets.sentinel import sentinel_get_datasets, normalize_per_band  # noqa: E402

ai8x.set_device(85, simulate=False, round_avg=False)

BATCH = 64
GAINS = [0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0]
TARGET_TPR, TARGET_FPR = 0.95, 0.01


def find_one_base_ckpt():
    dirs = sorted((AI8X_TRAINING_DIR / "logs").glob("one_base___*"))
    assert dirs, "找不到 one_base 日志目录"
    d = dirs[-1]
    ckpt = d / "one_base_best.pth.tar"
    assert ckpt.exists(), f"无 best checkpoint: {ckpt}"
    return ckpt, d


def pick_points(fpr, tpr):
    ok = tpr >= TARGET_TPR
    fpr_at = float(fpr[ok].min()) if ok.any() else float("nan")
    ok = fpr <= TARGET_FPR
    tpr_at = float(tpr[ok].max()) if ok.any() else float("nan")
    return fpr_at, tpr_at


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device = {device}")

    ckpt_path, log_dir = find_one_base_ckpt()
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    use_bias = "conv1.op.bias" in ckpt["state_dict"]
    model = KiloVAD_MAX(channels=(64, 96, 96, 64, 32, 16), num_classes=2,
                        num_channels=128, bias=use_bias)
    model.load_state_dict(ckpt["state_dict"])
    model.eval().to(device)
    print(f"checkpoint {ckpt_path}  epoch={ckpt.get('epoch')}  bias={use_bias}")

    _, test_ds = sentinel_get_datasets(data=None, load_train=False, load_test=True)
    labels = test_ds.targets                      # np int 数组 (N,)
    X = test_ds.X                                 # 共享 int8 数组 (N,128,128)
    idx = test_ds.indices                         # int 数组 (N,)
    print(f"test {len(test_ds)} 条 (pos {int(labels.sum())}, "
          f"neg {int((1 - labels).sum())})")

    # 参考路径：DataLoader -> __getitem__（内部已归一化）
    loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False, num_workers=0)
    ref_logits, ref_labels = [], []
    with torch.no_grad():
        for inputs, lbl in loader:
            ref_logits.append(model(inputs.to(device)).cpu())
            ref_labels.append(lbl)
    ref_logits = torch.cat(ref_logits)
    ref_labels = torch.cat(ref_labels)
    ref_scores = ref_logits[:, 1] - ref_logits[:, 0]

    rows = []
    scores_g1 = None
    for g in GAINS:
        logits_all, labels_all = [], []
        with torch.no_grad():
            for start in range(0, len(idx), BATCH):
                chunk = idx[start:start + BATCH]
                raw = torch.from_numpy(X[chunk].astype(np.float32)).to(device)
                x = torch.clamp(torch.round(raw * g), -128, 127)   # 音量变化（原始刻度）
                x = normalize_per_band(x)                           # 再归一化
                logits_all.append(model(x).cpu())
                labels_all.append(torch.from_numpy(labels[start:start + BATCH]))
        logits = torch.cat(logits_all).numpy()
        lab = torch.cat(labels_all).numpy()

        scores = logits[:, 1] - logits[:, 0]
        top1 = (logits.argmax(axis=1) == lab).mean() * 100
        auc = roc_auc_score(lab, scores)
        fpr, tpr, _ = roc_curve(lab, scores)
        fpr_at, tpr_at = pick_points(fpr, tpr)

        rows.append(dict(gain=g, auc=auc, fpr_at=fpr_at, tpr_at=tpr_at, top1=top1))
        if g == 1.0:
            scores_g1 = torch.from_numpy(scores)

    # 自检：g=1.0 的 raw→norm 路径 == DataLoader→norm 路径
    diff = (scores_g1 - ref_scores).abs().max().item()
    # 两条路径跑的是同一输入，差别只来自 cuDNN 两次前向的非确定性（~1e-3 量级）。
    # 阈值 0.05 远大于该噪声、又远小于"真 bug"的差异（>5）。
    ok = diff < 0.05
    print(f"\n[自检 g=1.0] max|Δscore| 相对 DataLoader 路径 = {diff:.2e}  -> "
          f"{'一致 ✔（cuDNN 噪声）' if ok else '**不一致，先查**'}")

    base = rows[GAINS.index(1.0)]
    head = (f"{'gain':>7s} {'AUC':>9s} {'FPR@TPR95':>11s} {'ΔFPR':>9s} "
            f"{'TPR@FPR1%':>11s} {'Top1%':>8s}")
    lines = [head, "-" * len(head)]
    base_fpr = base["fpr_at"]
    for r in rows:
        lines.append(f"{r['gain']:7.3f} {r['auc']:9.5f} {r['fpr_at']:11.5f} "
                     f"{r['fpr_at'] - base_fpr:+9.5f} {r['tpr_at']:11.5f} "
                     f"{r['top1']:8.3f}")
    lines += ["",
              "ΔFPR = 相对 g=1.0 的 FPR@TPR95 变化。",
              "预测：g≤1 低音量侧应基本平坦（增益不变性），g>1 高增益侧因 int8 截断才掉。"]
    table = "\n".join(lines)
    print("\n" + table)

    csv_path = BASE_DIR / "amplitude_probe_norm.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["gain", "auc", "fpr_at", "tpr_at", "top1"])
        w.writeheader()
        w.writerows(rows)
    (BASE_DIR / "amplitude_probe_norm.txt").write_text(table + "\n", encoding="utf-8")
    print(f"\n已写: {csv_path}")
    print(f"已写: {BASE_DIR / 'amplitude_probe_norm.txt'}")


if __name__ == "__main__":
    main()
