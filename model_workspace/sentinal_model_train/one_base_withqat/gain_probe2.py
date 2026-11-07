# -*- coding: utf-8 -*-
"""
增益 k 标定（修正版）。

上一版发现的问题：ai8x.py:813 `if not dev.simulate: out_shift = out_shift - activation_threshold`
—— simulate 模式默认 `-q` checkpoint 里 output_shift 已经减过 threshold，但这个 checkpoint 没有
（conv1: out_shift=-4, thr=4）。结果 conv3 起激活全被压成 {0,127}，输出与输入无关。

这里同时跑两种口径：
   A) simulate 用原始 output_shift（ai8x 原逻辑）
   B) simulate 用 output_shift - activation_threshold（即 QAT 前向的口径）
然后各自扫 k，看哪种口径能得到健康的分层激活 + 与浮点一致的判定。

x_int8 = round(ref * k)，ref = 训练侧 normalize_per_band 输出。
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
KS = [1, 2, 4, 8, 16, 32]
LAYERS = ["conv1", "conv2", "conv3", "conv4", "conv5", "conv6", "fc"]


def setup():
    os.chdir(TRAIN)
    sys.path.insert(0, TRAIN)
    spec = importlib.util.spec_from_file_location(
        "sm", os.path.join(TRAIN, "models", "sentinel.py"))
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    return sm.KiloVAD_MAX


def load_ckpt(name):
    ck = torch.load(os.path.join(LOG, name), map_location="cpu", weights_only=False)
    return {(k[7:] if k.startswith("module.") else k): v for k, v in ck["state_dict"].items()}


def load_test():
    rng = np.random.default_rng(7)
    xs, ys = [], []
    for name, tag in (("pos", 1), ("neg", 0)):
        m = np.load(os.path.join(DATA, f"{name}_X.npy"), mmap_mode="r")
        sp = np.load(os.path.join(DATA, f"{name}_split.npy"))
        idx = np.flatnonzero(sp == 2)
        idx = rng.choice(idx, size=min(N_TEST // 2, len(idx)), replace=False)
        idx.sort()
        xs.append(np.asarray(m[idx], dtype=np.float32))
        ys.append(np.full(len(idx), tag, dtype=np.int64))
    X = np.concatenate(xs, 0)
    y = np.concatenate(ys, 0)
    R = (X - X.mean(axis=-1, keepdims=True)) / (X.std(axis=-1, ddof=1, keepdims=True) + EPS)
    return R.astype(np.float32), y


@torch.no_grad()
def margins(model, X, bs=64):
    out = []
    for i in range(0, len(X), bs):
        lg = model(torch.as_tensor(X[i:i + bs], dtype=torch.float32))
        out.append((lg[:, 1] - lg[:, 0]).cpu().numpy())
    return np.concatenate(out)


@torch.no_grad()
def layer_uniq(model, x):
    acts, hs = {}, []
    for n in LAYERS:
        hs.append(getattr(model, n).register_forward_hook(
            lambda mod, i, o, n=n: acts.__setitem__(n, len(torch.unique(o.detach())))))
    model(x)
    for h in hs:
        h.remove()
    return acts


def main():
    K = setup()
    R, y = load_test()
    print(f"测试 {R.shape}  人声 {int((y==1).sum())} / 非人声 {int((y==0).sum())}")
    print(f"ref 范围 [{R.min():.2f}, {R.max():.2f}]\n")

    import ai8x
    sd_f = load_ckpt("one_base_best.pth.tar")
    sd_q = load_ckpt("one_base_qat_best-q.pth.tar")

    ai8x.set_device(85, simulate=False, round_avg=False)
    m_f = K()
    m_f.load_state_dict(sd_f)
    m_f.eval()
    m_ref = margins(m_f, R)
    print(f"[基准] 浮点模型 @ref: acc={100*( (m_ref>0)==(y==1) ).mean():.2f}%")

    ai8x.set_device(85, simulate=True, round_avg=False)
    for variant in ("A_raw", "B_minus_thr"):
        m_q = K()
        m_q.load_state_dict(sd_q)
        if variant == "B_minus_thr":
            for n in LAYERS:
                mod = getattr(m_q, n)
                mod.output_shift.data = (mod.output_shift.data
                                         - mod.activation_threshold.data).clamp(-15., 15.)
        m_q.eval()
        print(f"\n=== 口径 {variant} ===")
        for k in KS:
            Xk = np.clip(np.round(R * k), -128, 127)
            m = margins(m_q, Xk)
            pred = (m > 0).astype(np.int64)
            acc = 100.0 * float((pred == y).mean())
            agree = 100.0 * float((pred == (m_ref > 0)).mean())
            print(f"  k={k:<4d} acc={acc:5.2f}%  与浮点一致={agree:5.2f}%  "
                  f"score[{m.min():9.1f},{m.max():9.1f}] 覆盖 {len(np.unique(m))}")
        # 分层激活健康度（k=8 为例）
        u = layer_uniq(m_q, torch.as_tensor(np.clip(np.round(R[:4] * 8), -128, 127)))
        print(f"  k=8 分层唯一值数: " + "  ".join(f"{n}={u[n]}" for n in LAYERS))


if __name__ == "__main__":
    main()
