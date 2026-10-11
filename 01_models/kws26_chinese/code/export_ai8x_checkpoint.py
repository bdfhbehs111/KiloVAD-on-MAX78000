# -*- coding: utf-8 -*-
"""
把 PyTorch 训练的 30K 学生权重迁移成 ai8x 格式 checkpoint（供 quantize.py / ai8xize.py 用）。

映射关系：
  PyTorch nn.Conv1d  →  ai8x Conv1d 内部 op
  conv1.0.weight     →  conv1.op.weight
  conv2.1.weight     →  conv2.op.weight   （Sequential 里 MaxPool 占 idx 0）
  fc.weight          →  fc.op.weight
"""
import os
import sys

AI8X_DIR = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\ai8x-training"
sys.path.insert(0, AI8X_DIR)

import torch
from torch import nn
import ai8x

ai8x.set_device(85, simulate=True, round_avg=False)

HERE = os.path.dirname(os.path.abspath(__file__))
_candidates = [os.path.join(HERE, "student_kws_weights.pth.tar"),
               os.path.join(os.path.dirname(HERE), "student_kws_weights.pth.tar")]
PT_WEIGHTS = next(p for p in _candidates if os.path.exists(p))
OUT = os.path.join(HERE, "kws26_ai8x.pth.tar")
ARCH = "ai85kws26"
NUM_CLASSES = 26
WIDTH = (32, 48, 32, 64)


class StudentAI8X(nn.Module):
    def __init__(self, width=WIDTH, num_classes=NUM_CLASSES):
        super().__init__()
        c1, c2, c3, c4 = width
        self.conv1 = ai8x.FusedConv1dReLU(128, c1, 3, stride=1, padding=0, bias=True)
        self.conv2 = ai8x.FusedMaxPoolConv1dReLU(c1, c2, 3, pool_size=2, pool_stride=2,
                                                 stride=1, padding=1, bias=True)
        self.conv3 = ai8x.FusedMaxPoolConv1dReLU(c2, c3, 3, pool_size=9, pool_stride=9,
                                                 stride=1, padding=1, bias=True)
        self.conv4 = ai8x.FusedMaxPoolConv1dReLU(c3, c4, 3, pool_size=7, pool_stride=7,
                                                 stride=1, padding=1, bias=True)
        self.fc = ai8x.Linear(c4, num_classes, bias=True, wide=True)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


MAPPING = {
    "conv1.0.weight": "conv1.op.weight", "conv1.0.bias": "conv1.op.bias",
    "conv2.1.weight": "conv2.op.weight", "conv2.1.bias": "conv2.op.bias",
    "conv3.1.weight": "conv3.op.weight", "conv3.1.bias": "conv3.op.bias",
    "conv4.1.weight": "conv4.op.weight", "conv4.1.bias": "conv4.op.bias",
    "fc.weight": "fc.op.weight", "fc.bias": "fc.op.bias",
}

pt = torch.load(PT_WEIGHTS, map_location="cpu", weights_only=False)
pt_sd = pt["state_dict"]
print("PyTorch 权重 key:")
for k in pt_sd:
    if "weight" in k or "bias" in k:
        print(f"  {k:24s} {tuple(pt_sd[k].shape)}")
print(f"（记录准确率 val_acc={pt.get('val_acc')}）")

model = StudentAI8X()
full = model.state_dict()
mapped = 0
for pk, ak in MAPPING.items():
    if pk in pt_sd:
        assert full[ak].shape == pt_sd[pk].shape, f"{pk} 形状不匹配"
        full[ak] = pt_sd[pk].clone()
        mapped += 1
    else:
        print(f"  ⚠ 缺失 {pk}")
model.load_state_dict(full)
print(f"\n✅ 迁移 {mapped}/{len(MAPPING)} 个权重张量")

# 前向自检
with torch.no_grad():
    y = model(torch.randn(1, 128, 128))
print("前向输出:", tuple(y.shape))

torch.save({
    "epoch": 0,
    "state_dict": model.state_dict(),
    "arch": ARCH,
    "optimizer_state_dict": None,
    "optimizer_type": None,
    "compression_sched": None,
    "extras": {"val_acc": pt.get("val_acc"), "classes": pt.get("classes")},
}, OUT)
print(f"已保存 ai8x checkpoint: {OUT}")
