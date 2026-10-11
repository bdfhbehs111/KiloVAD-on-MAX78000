# -*- coding: utf-8 -*-
"""
主体识别（人声）学生模型 —— 与哨兵共前端（折叠 PCM）

任务：判"人声 vs 非人声"（2 分类）
- 输入：折叠 PCM (B, 128, 128)，[-128,127]（与哨兵一致）
- 输出：128 维 embedding + 2 分类 logits（推理）+ 768 维投影（蒸馏对齐教师 WavLM）

结构约束：符合 MAX78000 CNN 加速器（padding∈{0,1,2}、kernel∈{1..9}、无 pool 时 stride=1）
参数量：约 8.6 万
"""
import torch
import torch.nn as nn


class StudentNet(nn.Module):
    def __init__(self, emb_dim=128, num_classes=2, teacher_dim=768, width=None):
        """width=(c1,c2,c3,c4) 控制 4 层通道数；None = 默认（约 8.6 万部署参数）"""
        super().__init__()
        c1, c2, c3, c4 = tuple(width) if width else (64, 96, 64, emb_dim)
        self.emb_dim = c4
        # 折叠 PCM (128,128) → 1D 卷积沿时间维
        self.conv1 = nn.Sequential(                      # (c1, 126)
            nn.Conv1d(128, c1, kernel_size=3, stride=1, padding=0, bias=True),
            nn.ReLU(),
        )
        self.conv2 = nn.Sequential(                      # pool2 → (c2, 63)
            nn.MaxPool1d(2),
            nn.Conv1d(c1, c2, kernel_size=3, stride=1, padding=1, bias=True),
            nn.ReLU(),
        )
        self.conv3 = nn.Sequential(                      # pool9 → (c3, 7)
            nn.MaxPool1d(9),
            nn.Conv1d(c2, c3, kernel_size=3, stride=1, padding=1, bias=True),
            nn.ReLU(),
        )
        self.conv4 = nn.Sequential(                      # pool7 → (c4, 1)
            nn.MaxPool1d(7),
            nn.Conv1d(c3, c4, kernel_size=3, stride=1, padding=1, bias=True),
            nn.ReLU(),
        )
        self.fc = nn.Linear(c4, num_classes)             # 分类头（推理用）
        self.proj = nn.Linear(c4, teacher_dim)           # 投影头（蒸馏用，仅训练）

    def forward(self, x, return_proj=False):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        emb = x.view(x.size(0), -1)                      # conv4 输出 T=1，摊平 → (B, c4)
        logits = self.fc(emb)
        if return_proj:
            return emb, logits, self.proj(emb)
        return emb, logits


def count_params(model):
    return sum(p.numel() for p in model.parameters())


if __name__ == '__main__':
    print("=== 不同宽度的部署参数量 ===")
    for w in [(64, 96, 64, 128), (48, 64, 48, 96), (32, 48, 32, 64), (24, 32, 24, 48)]:
        m = StudentNet(width=w)
        deploy = count_params(m) - sum(p.numel() for p in m.proj.parameters())
        print(f"  width={str(w):20s} 部署参数 {deploy:,}")

    m = StudentNet(width=(32, 48, 32, 64))
    x = torch.randn(2, 128, 128)
    emb, logits, proj = m(x, return_proj=True)
    print("\nemb:", tuple(emb.shape), "logits:", tuple(logits.shape), "proj:", tuple(proj.shape))
