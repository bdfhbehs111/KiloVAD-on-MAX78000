"""E2 —— 逐带归一化 sanity check（不训练，离线验证 normalize_per_band 本身）。

验证三件事：
  1. 真实样本：逐通道（axis 0）沿时间轴（axis 1）归一化后 mean≈0、std≈1
  2. 全零窗口：std=0 时 eps 护栏生效，不产生 NaN/inf，输出仍为 0
  3. 增益不变性：normalize(clip(round(x·g))) ≈ normalize(x)，g<1 无截断时应几乎相等
     （这是 E2 能杀幅度侧信道的数学根据；偏差来自 int8 量化粒度）

用 mmap 读 npy，不把 3.5GB 全载入内存。
"""

import importlib.util
from pathlib import Path

import numpy as np
import torch

BASE = Path(__file__).resolve().parent
AI8X = BASE / "ai8x-training"
SENTINEL = AI8X / "datasets" / "sentinel.py"

# 直接按文件路径加载模块，绕开 datasets/__init__ 的潜在副作用
spec = importlib.util.spec_from_file_location("sentinel_mod", str(SENTINEL))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
normalize_per_band = mod.normalize_per_band
POS_DIR = mod.POS_DIR

ok = True


def check(name, cond, detail=""):
    global ok
    mark = "PASS" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"[{mark}] {name}  {detail}")


# ---- 1. 真实样本逐通道统计 ----
pos_X = np.load(Path(POS_DIR) / "pos_X.npy", mmap_mode="r")   # (N,128,128) int8, 惰性映射
x = torch.from_numpy(np.ascontiguousarray(pos_X[0]).astype(np.float32))
y = normalize_per_band(x)                                     # (128,128)
mean = y.mean(dim=-1)
std = y.std(dim=-1)
check("真实样本逐通道 mean≈0", mean.abs().max().item() < 1e-4,
      f"max|mean|={mean.abs().max().item():.2e}")
check("真实样本逐通道 std≈1", (std - 1).abs().max().item() < 1e-3,
      f"std ∈ [{std.min().item():.4f}, {std.max().item():.4f}]")
check("无 NaN/inf", torch.isfinite(y).all().item())

# ---- 2. 全零窗口 ----
z = normalize_per_band(torch.zeros(128, 128))
check("全零窗口不爆", torch.isfinite(z).all().item() and z.abs().max().item() == 0,
      f"absmax={z.abs().max().item():.2e}")

# 常量非零通道（std=0 但 mean≠0）
c = normalize_per_band(torch.full((128, 128), 50.0))
check("常量通道不爆", torch.isfinite(c).all().item() and c.abs().max().item() == 0,
      f"absmax={c.abs().max().item():.2e}")

# ---- 3. 增益不变性（用几个真实样本）----
print("\n增益不变性 normalize(g·x) vs normalize(x)  (偏差来自 int8 量化，非归一化本身):")
for i in range(3):
    xi = torch.from_numpy(np.ascontiguousarray(pos_X[i]).astype(np.float32))
    yi = normalize_per_band(xi)
    for g in (0.5, 0.25, 0.125, 0.0625):
        xg = torch.clamp(torch.round(xi * g), -128, 127)
        yg = normalize_per_band(xg)
        d = (yg - yi).abs()
        print(f"  sample{i} g={g:6.4f}  max|Δ|={d.max().item():.4f}  "
              f"mean|Δ|={d.mean().item():.5f}")

print("\n" + ("== 全部通过 ==" if ok else "== 存在 FAIL，先查 =="))
