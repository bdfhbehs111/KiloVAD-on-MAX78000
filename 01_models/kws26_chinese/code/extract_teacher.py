# -*- coding: utf-8 -*-
"""
提取教师（WavLM）embedding，缓存供蒸馏训练使用。

产出：
  human_teacher_embs.npy     (N, 768)  人声片段的 WavLM embedding
  nonhuman_teacher_embs.npy  (M, 768)  非人声片段的 WavLM embedding

教师 embedding = WavLM 最后一层 hidden state 沿时间维 mean-pool。
"""
import os
import numpy as np
import torch
from transformers import WavLMConfig, WavLMModel

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "microsoft/wavlm-base-plus"
FS = 16000


def load_teacher():
    config = WavLMConfig.from_pretrained(MODEL)
    model = WavLMModel.from_pretrained(MODEL, config=config)
    model.eval()
    return model


@torch.no_grad()
def extract(segs_int16, model, device, batch_size=32):
    """(N, 16384) int16 → (N, 768) embedding"""
    embs = []
    n = len(segs_int16)
    for i in range(0, n, batch_size):
        batch = torch.from_numpy(
            segs_int16[i:i + batch_size].astype(np.float32) / 32768.0
        ).to(device)
        out = model(batch)
        embs.append(out.last_hidden_state.mean(dim=1).cpu())   # (B, 768)
        if (i // batch_size) % 20 == 0:
            print(f"  教师提取 {min(i + batch_size, n)}/{n}")
    return torch.cat(embs, dim=0).numpy()


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"设备: {device}")
    model = load_teacher().to(device)

    for name, out in [("human", "human_teacher_embs.npy"),
                      ("nonhuman", "nonhuman_teacher_embs.npy")]:
        src = os.path.join(HERE, f"{name}_segs.npy")
        dst = os.path.join(HERE, out)
        if not os.path.exists(src):
            print(f"缺少 {src}，跳过")
            continue
        if os.path.exists(dst):
            print(f"{out} 已存在，跳过")
            continue
        segs = np.load(src)
        print(f"{name}: {segs.shape} 段 → 提取教师 embedding")
        embs = extract(segs, model, device)
        np.save(dst, embs)
        print(f"  已保存 {out} {embs.shape}")


if __name__ == '__main__':
    main()
