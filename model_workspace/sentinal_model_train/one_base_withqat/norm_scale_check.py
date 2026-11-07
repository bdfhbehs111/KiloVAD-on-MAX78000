# -*- coding: utf-8 -*-
"""
离线验证：上板 C 代码里的「逐带归一化 + 重量化乘数」到底该取多少。

结论要回答两个问题：
  Q1  归一化后 |x| 的最大值是多少？→ 决定 ×k 里 k 该多大（k*max|x| 要刚好贴 127）
  Q2  用总体标准差(÷128)还是无偏(÷127)、以及 ×8 vs ×16，会差多少？

训练侧语义（datasets/sentinel.py::normalize_per_band，torch 默认无偏 std）：
    mean = x.mean(dim=-1)            # 沿 dim1（时间块轴）
    std  = x.std(dim=-1)             # torch 默认 unbiased=True → 除 (T-1)=127
    xn   = (x - mean) / (std + 1e-5)
样本形状 (128,128) = (dim0 块内采样位置, dim1 时间块)。

用 mmap 只读需要的样本，避免把两个 1.65 GB 的 npy 全读进内存。
"""
import json
import os

import numpy as np

D = (r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000"
     r"\model_workspace\sentinal_dataset\dataset_processed")

N_PER_CLASS = 300
EPS = 1e-5


def load_subset():
    rng = np.random.default_rng(1234)
    xs, ys = [], []
    for name, tag in (("pos", 1), ("neg", 0)):
        m = np.load(os.path.join(D, f"{name}_X.npy"), mmap_mode="r")
        idx = rng.choice(len(m), size=min(N_PER_CLASS, len(m)), replace=False)
        idx.sort()
        xs.append(np.asarray(m[idx], dtype=np.float32))
        ys.append(np.full(len(idx), tag, dtype=np.int8))
    return np.concatenate(xs, 0), np.concatenate(ys, 0)


def norm(x, ddof):
    m = x.mean(axis=-1, keepdims=True)
    s = x.std(axis=-1, ddof=ddof, keepdims=True)
    return (x - m) / (s + EPS)


def pct(a, q):
    return float(np.percentile(a, q))


def main():
    X, y = load_subset()
    print(f"样本 {X.shape}  int8 取值范围 [{X.min()}, {X.max()}]  "
          f"正样本 {int(y.sum())} / 负样本 {int((1 - y).sum())}")
    print()

    # ---- 训练语义：无偏 std（torch 默认），沿 dim1 ----
    R = norm(X, ddof=1)
    amax = np.abs(R).max(axis=(1, 2))

    print("Q1  每条样本 normalize 之后 |x| 的最大值（决定乘数）")
    for q in (50, 90, 99, 99.9):
        print(f"    p{q:<5}= {pct(amax, q):6.2f}")
    print(f"    max  = {amax.max():6.2f}")
    print(f"    超过 16 的样本占比 : {100.0 * (amax > 16).mean():5.2f} %")
    print(f"    → 若乘数 k 满足 k*16 = 128，则 k = {128.0 / max(amax.max(), 1e-9):.3f}"
          f"（按全库最大 {amax.max():.2f} 算）")
    print()

    print("Q2  不同乘数下的截断（clamp）比例")
    for k in (4, 8, 16, 32):
        sat = np.abs(R * k) > 127.0
        print(f"    ×{k:<3d}  |q|>127 的元素 {100.0 * sat.mean():7.4f} %   "
              f"受影响样本 {100.0 * sat.any(axis=(1, 2)).mean():6.2f} %")
    print()

    print("Q3  总体 std(÷128) vs 无偏 std(÷127) 的实际差异")
    R0 = norm(X, ddof=0)
    Qa = np.clip(np.round(R * 8.0), -128, 127).astype(np.int16)
    Qb = np.clip(np.round(R0 * 8.0), -128, 127).astype(np.int16)
    diff = Qa != Qb
    print(f"    ×8 定点后元素不同 : {100.0 * diff.mean():6.3f} %")
    print(f"    平均 |Δ| (int8 单位): {np.abs(Qa - Qb).mean():6.3f} / 128")
    print(f"    最大 |Δ|           : {int(np.abs(Qa - Qb).max())}")
    print()

    print("Q4  全零 / 近静音通道（std 落在 eps 护栏上）")
    s_per_band = X.std(axis=-1, ddof=1)
    print(f"    std == 0 的通道占比         : {100.0 * (s_per_band == 0).mean():6.3f} %")
    print(f"    std <  1 (int8 LSB) 的通道占比: {100.0 * (s_per_band < 1).mean():6.3f} %")
    print()

    # ---- 逐类看：人声是否本来就"更响"（归一化后应该被抹平）----
    print("Q5  归一化是否真的抹平了幅度侧信道")
    peak = np.abs(X).max(axis=(1, 2))
    for tag, name in ((1, "人声"), (0, "非人声")):
        m = y == tag
        print(f"    {name:<4} 归一化前 |x| 峰值 中位数 {pct(peak[m], 50):6.1f}   "
              f"归一化后 {pct(amax[m], 50):5.2f}")
    print()

    out = {
        "n_samples": int(len(X)),
        "orig_max_ddof1": float(amax.max()),
        "orig_p99_ddof1": pct(amax, 99),
        "suggest_k": 128.0 / max(amax.max(), 1e-9),
        "sat_frac_x8": float((np.abs(R * 8) > 127).mean()),
        "sat_frac_x16": float((np.abs(R * 16) > 127).mean()),
        "int8_diff_pop_vs_unbiased_pct": float(100.0 * diff.mean()),
        "zero_band_pct": float(100.0 * (s_per_band == 0).mean()),
    }
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "norm_scale_check.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[written] {p}")


if __name__ == "__main__":
    main()
