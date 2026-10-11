# -*- coding: utf-8 -*-
"""
KWS 数据准备（多分类）：SynTTS 25 个中文命令（正样本）+ ESC-50（负样本）

产出：
  kws_segs.npy    int16 (N, 16384)  音频片段
  kws_labels.npy  int64 (N,)        类别标签（0~24 = 命令，25 = 负样本/其他）
  kws_classes.json                  类别名映射

说明：
  - 统一 16kHz、单声道、16384 点/片段
  - 命令音频短则补零、长则取中心 16384 点
"""
import os
import glob
import json
import zipfile
import numpy as np
from math import gcd
from scipy.io import wavfile
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
FS = 16000
SEG_LEN = 16384          # 128 * 128
MAX_PER_CLASS = 800      # 每个命令最多取多少条（平衡）
MAX_NEG = 6000           # 负样本最多取多少条


def load_wav_16k(path):
    sr, data = wavfile.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    else:
        data = data.astype(np.float32)
    if sr != FS:
        g = gcd(sr, FS)
        data = resample_poly(data, FS // g, sr // g)
    return data.astype(np.float32)


def to_seg(data):
    """取 16384 点：短则补零，长则取中心"""
    if len(data) >= SEG_LEN:
        start = (len(data) - SEG_LEN) // 2
        return data[start:start + SEG_LEN]
    return np.pad(data, (0, SEG_LEN - len(data)))


def to_int16(seg_f32):
    return np.clip(np.round(seg_f32 * 32767), -32768, 32767).astype(np.int16)


def extract_zips(syn_dir, out_dir):
    """解压 25 个命令 zip 到 out_dir/<命令名>/"""
    os.makedirs(out_dir, exist_ok=True)
    zips = sorted(glob.glob(os.path.join(syn_dir, "*.zip")))
    for z in zips:
        name = os.path.splitext(os.path.basename(z))[0]
        dst = os.path.join(out_dir, name)
        if not os.path.exists(dst) or not os.listdir(dst):
            os.makedirs(dst, exist_ok=True)
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
    return sorted(d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d)))


def main():
    rng = np.random.default_rng(0)
    syn_dir = os.path.join(HERE, "SynTTS-Free-ST-Chinese", "Free_ST_Chinese")
    ext_dir = os.path.join(HERE, "SynTTS-extracted")

    print("解压 SynTTS zip...")
    classes = extract_zips(syn_dir, ext_dir)
    print(f"共 {len(classes)} 个命令类: {classes}")

    segs, labels = [], []
    for ci, cname in enumerate(classes):
        wavs = glob.glob(os.path.join(ext_dir, cname, "**", "*.wav"), recursive=True)
        if len(wavs) > MAX_PER_CLASS:
            idx = rng.choice(len(wavs), MAX_PER_CLASS, replace=False)
            wavs = [wavs[i] for i in idx]
        ok = 0
        for w in wavs:
            try:
                segs.append(to_int16(to_seg(load_wav_16k(w))))
                labels.append(ci)
                ok += 1
            except Exception:
                pass
        print(f"  [{ci:2d}] {cname:16s} {ok} 条")

    # 负样本：ESC-50
    print("负样本（ESC-50）...")
    esc_audio = os.path.join(HERE, "ESC-50-master", "audio")
    esc_wavs = sorted(glob.glob(os.path.join(esc_audio, "*.wav")))
    neg = []
    for w in esc_wavs:
        if len(neg) >= MAX_NEG:
            break
        try:
            data = load_wav_16k(w)
        except Exception:
            continue
        n = len(data) // SEG_LEN
        for i in range(n):
            if len(neg) >= MAX_NEG:
                break
            neg.append(to_int16(data[i * SEG_LEN:(i + 1) * SEG_LEN]))
    for s in neg:
        segs.append(s)
        labels.append(len(classes))
    print(f"  负样本 {len(neg)} 条（类别 {len(classes)}）")

    X = np.stack(segs)
    y = np.array(labels, dtype=np.int64)
    np.save(os.path.join(HERE, "kws_segs.npy"), X)
    np.save(os.path.join(HERE, "kws_labels.npy"), y)
    with open(os.path.join(HERE, "kws_classes.json"), "w", encoding="utf-8") as f:
        json.dump(classes + ["_other_"], f, ensure_ascii=False, indent=2)
    print(f"\n总计 {len(X)} 条，{len(classes)+1} 类")
    print(f"已保存 kws_segs.npy {X.shape}, kws_labels.npy {y.shape}")


if __name__ == '__main__':
    main()
