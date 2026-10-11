# -*- coding: utf-8 -*-
"""
极简哨兵实验：折叠 PCM 输入的极小 CNN，目标 1K~5K 参数

任务：突发声（异常）vs 平稳背景（正常）—— 对标哨兵职责
方法：抄 DrongoNet 设计（极窄通道 + GAP + focal loss + 频率强调层替代 BN）
评测：baseline_16k.wav 上的正常/异常区分度（对比 7 万参数的 5.74）

数据：ESC-50（正常 16 类 + 异常 8 类）
"""
import os
import glob
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from math import gcd
from scipy.io import wavfile
from scipy.signal import resample_poly

FS = 16000
SEG_LEN = 16384          # 128*128
ESC = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\主体识别\ESC-50-master"
BASELINE = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\baseline_16k.wav"

NORMAL_CATS = ["rain", "wind", "sea_waves", "crickets", "vacuum_cleaner", "washing_machine",
               "engine", "train", "airplane", "helicopter", "clock_tick", "snoring",
               "breathing", "crackling_fire", "insects", "chainsaw"]
ANOMALY_CATS = ["glass_breaking", "door_wood_knock", "clapping", "fireworks",
                "siren", "car_horn", "clock_alarm", "thunderstorm"]


def load_wav_16k(path):
    sr, data = wavfile.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    else:
        data = data.astype(np.float32)
    if sr != FS:
        g = gcd(sr, FS)
        data = resample_poly(data, FS // g, sr // g)
    return data.astype(np.float32)


def to_folded(seg):
    """16384 点 float [-1,1] → (128,128) 折叠输入 [-128,127]"""
    step = 2.0 / 256
    q = np.clip(np.round((seg + 1.0) / step), 0, 255).astype(np.uint8)
    return (q.reshape(128, 128).T.astype(np.float32) - 128.0)


def load_esc_data():
    """ESC-50 → (X, y)，y=0 正常 / 1 异常（类别从 meta/esc50.csv 读取）"""
    import csv
    meta = {}
    with open(os.path.join(ESC, "meta", "esc50.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row["filename"]] = row["category"]

    X, y = [], []
    for label, cats in [(0, NORMAL_CATS), (1, ANOMALY_CATS)]:
        for fname, cat in sorted(meta.items()):
            if cat not in cats:
                continue
            p = os.path.join(ESC, "audio", fname)
            if not os.path.exists(p):
                continue
            try:
                d = load_wav_16k(p)
            except Exception:
                continue
            for i in range(len(d) // SEG_LEN):
                X.append(to_folded(d[i * SEG_LEN:(i + 1) * SEG_LEN]))
                y.append(label)
    return np.stack(X), np.array(y, dtype=np.int64)


# ---------------- 极简模型（DrongoNet 风格） ----------------
class FreqEmphasis(nn.Module):
    """可学习频率强调层（DrongoNet Eq.1）：X ⊙ σ(w·s)，仅 F+1 参数，量化安全（替代 BN）"""

    def __init__(self, n_freq):
        super().__init__()
        self.w = nn.Parameter(torch.ones(n_freq))
        self.s = nn.Parameter(torch.tensor(3.0))

    def forward(self, x):                       # x: (B, F, T)
        return x * torch.sigmoid(self.w.view(1, -1, 1) * self.s)


class TinySentinel(nn.Module):
    """折叠 PCM (128,128) → 极窄 CNN → GAP → embedding + logits"""

    def __init__(self, width=(8, 12, 16), num_classes=2, k1=3):
        super().__init__()
        c1, c2, c3 = width
        self.emb_dim = c3
        self.freq = FreqEmphasis(128)
        self.conv1 = nn.Sequential(                           # (c1, 128)
            nn.Conv1d(128, c1, kernel_size=k1, stride=1, padding=k1 // 2, bias=True),
            nn.ReLU(),
        )
        self.conv2 = nn.Sequential(                           # pool2 → (c2, 64)
            nn.MaxPool1d(2),
            nn.Conv1d(c1, c2, kernel_size=3, stride=1, padding=1, bias=True),
            nn.ReLU(),
        )
        self.conv3 = nn.Sequential(                           # pool4 → (c3, 16)
            nn.MaxPool1d(4),
            nn.Conv1d(c2, c3, kernel_size=3, stride=1, padding=1, bias=True),
            nn.ReLU(),
        )
        self.fc = nn.Linear(c3, num_classes)

    def forward(self, x, return_emb=False):
        x = self.freq(x)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        emb = x.mean(dim=2)                                   # GAP → (B, c3)
        logits = self.fc(emb)
        if return_emb:
            return emb, logits
        return logits


def count_params(m):
    return sum(p.numel() for p in m.parameters())


def focal_loss(logits, target, gamma=2.0):
    """focal 二分类交叉熵（DrongoNet 用 γ=2.0）"""
    logp = F.log_softmax(logits, dim=1)
    logpt = logp.gather(1, target.view(-1, 1)).squeeze(1)
    pt = logpt.exp()
    return -((1 - pt) ** gamma * logpt).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=str, default="8,12,16")
    ap.add_argument("--k1", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--tag", type=str, default="w8_12_16")
    args = ap.parse_args()

    torch.manual_seed(0)
    np.random.seed(0)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    width = tuple(int(v) for v in args.width.split(","))

    print("加载 ESC-50 数据...")
    X, y = load_esc_data()
    print(f"  共 {len(X)} 段：正常 {(y==0).sum()}，异常 {(y==1).sum()}")

    idx = np.random.permutation(len(X))
    n_val = len(X) // 8
    val_idx, tr_idx = idx[:n_val], idx[n_val:]

    Xt = torch.from_numpy(X).to(device)
    yt = torch.from_numpy(y).to(device)

    model = TinySentinel(width=width, k1=args.k1).to(device)
    print(f"模型 width={width} k1={args.k1} → 参数量 {count_params(model):,}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)

    B = 64
    best = 0.0
    for ep in range(1, args.epochs + 1):
        model.train()
        perm = torch.from_numpy(np.random.permutation(len(tr_idx))).to(device)
        tr = torch.from_numpy(tr_idx).to(device)
        tot = 0.0
        for i in range(0, len(perm), B):
            b = tr[perm[i:i + B]]
            logits = model(Xt[b])
            loss = focal_loss(logits, yt[b])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item()
        model.eval()
        with torch.no_grad():
            v = torch.from_numpy(val_idx).to(device)
            pred = model(Xt[v]).argmax(1)
            acc = (pred == yt[v]).float().mean().item()
        if ep % 10 == 0 or ep == 1:
            print(f"  epoch {ep:3d} loss {tot/max(1,len(perm)//B):.4f} val_acc {acc:.4f}")
        best = max(best, acc)
    print(f"最佳验证准确率: {best:.4f}")

    # ---------- 评测：baseline 上的正常/异常区分度 ----------
    print("\n=== baseline_16k.wav 区分度评测 ===")
    d = load_wav_16k(BASELINE)
    segs = [d[i * SEG_LEN:(i + 1) * SEG_LEN] for i in range(len(d) // SEG_LEN)]
    Xb = torch.from_numpy(np.stack([to_folded(s) for s in segs])).to(device)
    model.eval()
    with torch.no_grad():
        emb = model(Xb, return_emb=True)[0].cpu()

    # 已知异常：4.1s、5.1s（放手机）—— 对应片段 4、5
    anomaly_idx = [4, 5]
    normal_idx = [i for i in range(len(segs)) if i not in anomaly_idx]
    normal = emb[normal_idx]
    centroid = normal.mean(dim=0)
    d_n = torch.norm(normal - centroid, dim=1).mean().item()
    d_a = torch.norm(emb[anomaly_idx] - centroid, dim=1).mean().item()
    print(f"  正常片段到质心距离: {d_n:.2f}")
    print(f"  异常片段到质心距离: {d_a:.2f}")
    print(f"  区分度比值(异常/正常): {d_a / (d_n + 1e-8):.2f}")
    print(f"  [对比] 7 万参数哨兵的区分度: 5.74")

    # ---------- 保存权重 ----------
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             f"sentinel_tiny_{args.tag}.pth.tar")
    torch.save({
        "state_dict": model.state_dict(),
        "width": width, "k1": args.k1,
        "num_params": count_params(model),
        "val_acc": best, "auc_baseline_ratio": d_a / (d_n + 1e-8),
        "normal_cats": NORMAL_CATS, "anomaly_cats": ANOMALY_CATS,
    }, save_path)
    print(f"  已保存: {save_path}")


if __name__ == "__main__":
    main()
