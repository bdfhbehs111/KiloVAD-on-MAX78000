# -*- coding: utf-8 -*-
"""
KWS 多分类蒸馏：WavLM（教师）→ StudentNet（学生）

任务：折叠 PCM → 判"是哪个命令"（25 中文命令 + 1 其他/背景 = 26 类）
损失：α·MSE(学生投影, 教师embedding) + CE(学生logits, 标签)

前置：prepare_data_kws.py → kws_segs.npy / kws_labels.npy / kws_classes.json
产出：student_kws_weights.pth.tar
"""
import os
import json
import time
import argparse
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
from student import StudentNet, count_params

HERE = os.path.dirname(os.path.abspath(__file__))

BATCH_SIZE = 64
LR = 1.0e-3
EPOCHS = 60
ALPHA = 1.0
VAL_RATIO = 0.1
SEED = 0


def to_folded(segs_int16):
    """(N, 16384) int16 → (N, 128, 128) 折叠输入 [-128,127]"""
    segs = segs_int16.astype(np.float32) / 32768.0
    step = 2.0 / 256
    q = np.clip(np.round((segs + 1.0) / step), 0, 255).astype(np.uint8)
    folded = q.reshape(-1, 128, 128).transpose(0, 2, 1)
    return folded.astype(np.float32) - 128.0


def extract_teacher(segs_int16, cache):
    """提取/加载 WavLM 教师 embedding（768 维）"""
    if os.path.exists(cache):
        print(f"教师 embedding 已缓存：{cache}")
        return np.load(cache)
    from transformers import WavLMConfig, WavLMModel
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("加载 WavLM 教师...")
    model = WavLMModel.from_pretrained("microsoft/wavlm-base-plus").eval().to(device)
    embs = []
    n = len(segs_int16)
    with torch.no_grad():
        for i in range(0, n, 32):
            batch = torch.from_numpy(
                segs_int16[i:i + 32].astype(np.float32) / 32768.0).to(device)
            out = model(batch)
            embs.append(out.last_hidden_state.mean(dim=1).cpu())
            if (i // 32) % 50 == 0:
                print(f"  教师提取 {min(i+32, n)}/{n}")
    T = torch.cat(embs, dim=0).numpy()
    np.save(cache, T)
    print(f"已保存 {cache} {T.shape}")
    return T


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--lr", type=float, default=LR)
    parser.add_argument("--width", type=str, default="32,48,32,64",
                        help="四层通道数（逗号分隔）。32,48,32,64≈28K；64,96,64,128≈87K")
    args = parser.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"设备: {device}")

    X = np.load(os.path.join(HERE, "kws_segs.npy"))
    y = np.load(os.path.join(HERE, "kws_labels.npy"))
    with open(os.path.join(HERE, "kws_classes.json"), encoding="utf-8") as f:
        classes = json.load(f)
    n_classes = len(classes)
    print(f"数据 {X.shape}，{n_classes} 类")

    T = extract_teacher(X, os.path.join(HERE, "kws_teacher_embs.npy"))
    print("转换折叠输入...")
    Xf = to_folded(X)

    n = len(Xf)
    idx = np.random.permutation(n)
    n_val = int(n * VAL_RATIO)
    val_idx, tr_idx = idx[:n_val], idx[n_val:]

    def make_dl(indices, shuffle):
        ds = TensorDataset(torch.from_numpy(Xf[indices]),
                           torch.from_numpy(y[indices]),
                           torch.from_numpy(T[indices]))
        return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle, num_workers=0)

    dl_tr = make_dl(tr_idx, True)
    dl_val = make_dl(val_idx, False)

    width = tuple(int(v) for v in args.width.split(","))
    model = StudentNet(num_classes=n_classes, width=width).to(device)
    print(f"学生宽度: {width}")
    print(f"学生参数量: {count_params(model):,}")
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_acc = 0.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        tot_loss = tot_cls = tot_dist = 0.0
        for xb, yb, tb in dl_tr:
            xb, yb, tb = xb.to(device), yb.to(device), tb.to(device)
            emb, logits, proj = model(xb, return_proj=True)
            loss_dist = F.mse_loss(proj, tb)
            loss_cls = F.cross_entropy(logits, yb)
            loss = args.alpha * loss_dist + loss_cls
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot_loss += loss.item()
            tot_cls += loss_cls.item()
            tot_dist += loss_dist.item()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for xb, yb, _ in dl_val:
                xb, yb = xb.to(device), yb.to(device)
                _, logits = model(xb)
                correct += (logits.argmax(1) == yb).sum().item()
                total += len(yb)
        acc = correct / max(1, total)
        nb = len(dl_tr)
        print(f"epoch {epoch:3d} | loss {tot_loss/nb:.4f} "
              f"(cls {tot_cls/nb:.4f} dist {tot_dist/nb:.4f}) | val_acc {acc:.4f} "
              f"| {time.time()-t0:.1f}s")

        if acc >= best_acc:
            best_acc = acc
            torch.save({"state_dict": model.state_dict(),
                        "emb_dim": 128, "num_classes": n_classes,
                        "classes": classes, "val_acc": acc, "epoch": epoch},
                       os.path.join(HERE, "student_kws_weights.pth.tar"))
    print(f"\n最佳验证准确率: {best_acc:.4f}")
    print("已保存 student_kws_weights.pth.tar")


if __name__ == '__main__':
    main()
