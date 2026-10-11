# -*- coding: utf-8 -*-
"""
极简哨兵 → ai8x checkpoint（含 FreqEmphasis 折叠）

关键：FreqEmphasis 是逐通道缩放 x⊙g（MAX78000 不支持 depthwise），
      但它线性，可折叠进 conv1 权重：conv1(x⊙g) = (W⊙g)(x)
"""
import os
import sys

AI8X_DIR = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\ai8x-training"
sys.path.insert(0, AI8X_DIR)

import torch
import torch.nn as nn
import ai8x

ai8x.set_device(85, simulate=True, round_avg=False)

HERE = os.path.dirname(os.path.abspath(__file__))
PT_WEIGHTS = os.path.join(HERE, "sentinel_tiny_b2087.pth.tar")
OUT = os.path.join(HERE, "sentinel_tiny_ai8x.pth.tar")
ARCH = "ai85sentinel"


class TinySentinelAI8X(nn.Module):
    """上板版：FreqEmphasis 已折叠进 conv1"""

    def __init__(self, num_classes=2):
        super().__init__()
        self.conv1 = ai8x.FusedConv1dReLU(128, 8, 1, stride=1, padding=0, bias=True)
        self.conv2 = ai8x.FusedMaxPoolConv1dReLU(8, 12, 3, pool_size=2, pool_stride=2,
                                                 stride=1, padding=1, bias=True)
        self.conv3 = ai8x.FusedMaxPoolConv1dReLU(12, 16, 3, pool_size=4, pool_stride=4,
                                                 stride=1, padding=1, bias=True)
        self.pool = ai8x.AvgPool1d(16)
        self.fc = ai8x.Linear(16, num_classes, bias=True, wide=True)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


pt = torch.load(PT_WEIGHTS, map_location="cpu", weights_only=False)
sd = pt["state_dict"]
print(f"源模型: {pt['width']} k1={pt['k1']} 参数 {pt['num_params']} 区分度 {pt['auc_baseline_ratio']:.2f}")

# 折叠 FreqEmphasis 进 conv1
g = torch.sigmoid(sd["freq.w"] * sd["freq.s"])          # (128,)
print(f"频率强调增益范围: {g.min():.3f} ~ {g.max():.3f}")
w1 = sd["conv1.0.weight"] * g.view(1, -1, 1)            # (8, 128, 1) ⊙ g

MAPPING = {
    "conv1.op.weight": w1,
    "conv1.op.bias": sd["conv1.0.bias"],
    "conv2.op.weight": sd["conv2.1.weight"],
    "conv2.op.bias": sd["conv2.1.bias"],
    "conv3.op.weight": sd["conv3.1.weight"],
    "conv3.op.bias": sd["conv3.1.bias"],
    "fc.op.weight": sd["fc.weight"],
    "fc.op.bias": sd["fc.bias"],
}

model = TinySentinelAI8X()
full = model.state_dict()
mapped = 0
for ak, v in MAPPING.items():
    if ak not in full:
        print(f"  ⚠ ai8x 模型缺少 {ak}")
        continue
    assert full[ak].shape == v.shape, f"{ak}: {full[ak].shape} vs {v.shape}"
    full[ak] = v.clone()
    mapped += 1
model.load_state_dict(full)
print(f"✅ 迁移 {mapped}/{len(MAPPING)} 个张量")

n = sum(p.numel() for p in model.parameters())
print(f"ai8x 版参数量: {n:,}（FreqEmphasis 已折叠，减少 129）")

with torch.no_grad():
    y = model(torch.randn(1, 128, 128))
print("前向输出:", tuple(y.shape))

torch.save({
    "epoch": 0, "state_dict": model.state_dict(), "arch": ARCH,
    "optimizer_state_dict": None, "optimizer_type": None,
    "compression_sched": None,
    "extras": {"val_acc": pt.get("val_acc"), "ratio": pt.get("auc_baseline_ratio")},
}, OUT)
print(f"已保存: {OUT}")
