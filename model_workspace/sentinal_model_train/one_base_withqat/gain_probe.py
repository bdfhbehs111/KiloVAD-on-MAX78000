# -*- coding: utf-8 -*-
"""
增益系数 k 的离线标定。

问题：板上把逐带归一化后的浮点 ref 编成 int8 时，乘数 k 取多少才和训练/
ai8xize 的隐含假设一致？  `x_int8 = round(ref * k)`

做法（不靠推导，靠测）：
  1. 浮点模型 + 浮点权重，喂 ref          -> 基准准确率（应 ≈ 97.6%）
  2. 浮点模型 + 浮点权重，喂 round(ref*k) -> 看模型对输入增益有多敏感
  3. 量化模型(-q) + ai8x simulate=True，喂 round(ref*k)
     simulate 模式的 conv1 等价于 `round(acc_hw >> shift)` 的整数硬件行为，
     所以哪个 k 能让量化模型复现浮点模型的判定，那个 k 就是工具链的隐含输入尺度。

指标：voice=1 / nonvoice=0，score = logit1 - logit0，判定 score>0 为 voice。
      auc、acc、以及与浮点基准的一致率。
"""
import importlib.util
import os
import sys

import numpy as np
import torch

TRAIN = (r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000"
         r"\model_workspace\sentinal_model_train\ai8x-training")
LOG = os.path.join(TRAIN, r"logs\one_base_withqat___2026.11.04-104409")
DATA = (r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000"
        r"\model_workspace\sentinal_dataset\dataset_processed")

EPS = 1e-5
N_TEST = 400
KS = [1, 2, 4, 8, 16, 32, 64, 128]
SPLIT_TEST = 2


def load_model_class():
    os.chdir(TRAIN)
    sys.path.insert(0, TRAIN)
    spec = importlib.util.spec_from_file_location("sentinel_model", os.path.join(TRAIN, "models", "sentinel.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.KiloVAD_MAX


def load_ckpt(name):
    ck = torch.load(os.path.join(LOG, name), map_location="cpu", weights_only=False)
    sd = ck["state_dict"]
    return {(k[7:] if k.startswith("module.") else k): v for k, v in sd.items()}


def load_test():
    """返回 ref(float32 (N,128,128)) 和标签。ref 语义 = 训练侧 normalize_per_band。"""
    rng = np.random.default_rng(7)
    xs, ys = [], []
    want = N_TEST // 2
    for name, tag in (("pos", 1), ("neg", 0)):
        m = np.load(os.path.join(DATA, f"{name}_X.npy"), mmap_mode="r")
        sp = np.load(os.path.join(DATA, f"{name}_split.npy"))
        idx = np.flatnonzero(sp == SPLIT_TEST)
        idx = rng.choice(idx, size=min(want, len(idx)), replace=False)
        idx.sort()
        xs.append(np.asarray(m[idx], dtype=np.float32))
        ys.append(np.full(len(idx), tag, dtype=np.int64))
    X = np.concatenate(xs, 0)
    y = np.concatenate(ys, 0)
    mu = X.mean(axis=-1, keepdims=True)
    sd = X.std(axis=-1, ddof=1, keepdims=True)
    R = (X - mu) / (sd + EPS)
    return R.astype(np.float32), y


@torch.no_grad()
def margins(model, X, dtype=torch.float32, bs=64):
    out = []
    for i in range(0, len(X), bs):
        xb = torch.as_tensor(X[i:i + bs], dtype=dtype)
        lg = model(xb)
        out.append((lg[:, 1] - lg[:, 0]).cpu().numpy())
    return np.concatenate(out)


def auc(y, s):
    y = np.asarray(y)
    s = np.asarray(s, dtype=np.float64)
    pos = s[y == 1]
    neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.arange(1, len(order) + 1)
    s_pos = ranks[:len(pos)].sum()
    return float((s_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg)))


def report(tag, y, m):
    pred = (m > 0).astype(np.int64)
    acc = float((pred == y).mean())
    # 人声召回 / 非人声误报
    rec = float(pred[y == 1].mean()) if (y == 1).any() else float("nan")
    fpr = float(pred[y == 0].mean()) if (y == 0).any() else float("nan")
    print(f"    {tag:<22s} acc={acc*100:5.2f}%  auc={auc(y, m):.4f}  "
          f"人声召回={rec*100:5.1f}%  非人声误报={fpr*100:5.1f}%")
    return acc


def main():
    KiloVAD_MAX = load_model_class()
    R, y = load_test()
    print(f"测试样本 {R.shape}  人声 {int((y==1).sum())} / 非人声 {int((y==0).sum())}")
    print(f"ref 范围 [{R.min():.2f}, {R.max():.2f}]   |ref| 均值 {np.abs(R).mean():.3f}")
    print()

    sd_float = load_ckpt("one_base_best.pth.tar")
    sd_q = load_ckpt("one_base_qat_best-q.pth.tar")

    # ---------- 1. 浮点基准 ----------
    import ai8x
    ai8x.set_device(85, simulate=False, round_avg=False)
    m_f = KiloVAD_MAX()
    m_f.load_state_dict(sd_float)
    m_f.eval()

    print("[1] 浮点模型（基准）")
    m_ref = margins(m_f, R)
    acc_ref = report("ref (k=1)", y, m_ref)
    print()

    print("[2] 浮点模型吃 round(ref*k)：看增益敏感度")
    for k in KS:
        Xk = np.clip(np.round(R * k), -128, 127)
        sat = 100.0 * float((np.abs(R * k) > 127).mean())
        m = margins(m_f, Xk)
        acc = report(f"k={k:<4d} (饱和{sat:5.2f}%)", y, m)
        _ = acc
    print()

    # ---------- 3. 量化模型 + simulate ----------
    ai8x.set_device(85, simulate=True, round_avg=False)
    m_q = KiloVAD_MAX()
    m_q.load_state_dict(sd_q)
    m_q.eval()

    print("[3] 量化模型 (-q) + ai8x simulate=True：哪个 k 复现浮点判定")
    best_k, best = None, -1.0
    for k in KS:
        Xk = np.clip(np.round(R * k), -128, 127)
        m = margins(m_q, Xk)
        pred = (m > 0).astype(np.int64)
        agree = 100.0 * float((pred == (m_ref > 0)).mean())
        acc = float((pred == y).mean()) * 100.0
        rng = (float(m.min()), float(m.max()))
        print(f"    k={k:<4d} acc={acc:5.2f}%  与浮点一致={agree:5.2f}%  "
              f"score范围[{rng[0]:8.2f},{rng[1]:8.2f}]")
        if agree > best:
            best, best_k = agree, k
    print()
    print(f">>> 与浮点模型一致率最高的 k = {best_k}（{best:.2f}%）")


if __name__ == "__main__":
    main()
