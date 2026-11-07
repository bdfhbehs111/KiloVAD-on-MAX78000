"""E4b —— Optuna 多目标（Pareto）剪枝搜索

> **本目录是 `zero_base_last/` 的 one_base（逐带归一化）版。** 与旧版的三处差异：
>   1. 基线 checkpoint = `logs/one_base___2026.11.03-182532/one_base_best.pth.tar`
>   2. 文件从 `optuna.py` 改名 `optuna_search.py`：旧名会 shadow 掉 optuna 库
>   3. 重复性校验不再写死 zero_base 的 0.011809 / 0.996197，改成 --expect-fpr/--expect-auc
> 下面「搜索空间」那一节是 **zero_base 的 E1b 实测表**，它不是 one_base 的先验。
> 跑完 one_base 的 prunning.py 之后必须按新表重填 SPACE 才允许开搜。

======================================================================================
本脚本要回答的问题
======================================================================================
E1b 只做了**单层**敏感度（其它层保持 100%）。它给出的是**边界和方向**，不是答案：

  * 单层剪 75% 几乎全免费  ->  每一层单独都有很大冗余
  * 但 6 层同时剪到 75% 会怎样？**E1b 无法回答**（组合效应不可加）

E1c 就是把这个组合空间搜出来，而且是 **多目标**的：
    obj0 = 权重字节数     （MAX78000 的 weight memory，越小越好）
    obj1 = FPR@TPR=0.95   （误报率，越小越好）
两者天然冲突 —— 剪得越狠越省内存，但误报越高。没有唯一最优解，只有一条 Pareto 前沿。
**选哪个点，取决于你在板子上还剩多少 KB、以及你能接受多少误报。**

======================================================================================
搜索空间的每一个数字，都来自 **one_base 的 E4a 实测**（prune_e4a/results.csv，18 点）
======================================================================================
  baseline: W 79,392 B  cycles 118,272  val AUC 0.996105 / FPR 0.012627
                                     test AUC 0.995824 / FPR 0.010952

  layer  原通道   dAUC_val / dFPR_val  |  dAUC_test / dFPR_test
  ------ ------ ----------------------------------------------
  conv1    64   48ch +0.0000 +0.0012 | +0.0004 -0.0007
                32ch -0.0001 +0.0019 | +0.0008 -0.0018   <- 免费
                16ch -0.0018 +0.0155 | -0.0010 +0.0087   <- !! 唯一双向恶化 = 唯一的真信号
  conv2    96   72ch +0.0005 -0.0009 | -0.0003 +0.0017
                48ch -0.0002 +0.0010 | +0.0001 -0.0005
                24ch -0.0004 +0.0019 | -0.0001 +0.0008   <- 砍掉 34,560 B，仍接近免费
  conv3    96   72ch -0.0018 +0.0112 | +0.0001 +0.0033   <- 砍 25% 反而最伤 = 坏 seed
                48ch -0.0006 +0.0033 | -0.0003 +0.0011
                24ch -0.0009 +0.0033 | +0.0005 -0.0018   <- 非单调，噪声主导
  conv4    64   48ch +0.0002 -0.0005 | +0.0003 -0.0001
                32ch -0.0006 +0.0017 | +0.0004 -0.0019
                16ch -0.0008 +0.0030 | +0.0002 -0.0006
  conv5    32   24ch -0.0000 +0.0007 | +0.0001 -0.0001
                16ch -0.0000 +0.0005 | -0.0000 +0.0018
                 8ch -0.0000 +0.0028 | +0.0001 +0.0002   <- 全场最便宜的维度
  conv6    16   12ch -0.0011 +0.0039 | +0.0001 -0.0005
                 8ch -0.0012 +0.0063 | +0.0002 -0.0008
                 4ch +0.0002 -0.0003 | +0.0006 -0.0001   <- 只省 408 B，但确实免费

  **本表最重要的统计事实**：18 个点里，dFPR 在 val 与 test 上**符号一致只有 8 个**，
  spearman 0.008（≈完全无关）。mean(val−test) = +0.0043，sd = 0.0029。
  AUC 的同一比对：mean −0.00031，sd 0.00065。
  -> **FPR@TPR95 的单点排序在这个模型上不可用，AUC 才是可排序的轴。**
  -> 这是 Optuna 目标默认取 (cycles, auc_val)、而把 FPR 只作报告的原因。

cycle 分解（基线，Σ ceil(out/64)·in·k·T）：
    conv1 16,384 (14%)  conv2 49,152 (42%)  conv3 36,864 (31%)
    conv4  9,216 ( 8%)  conv5  6,144 ( 5%)  conv6    512 ( 0%)
  conv2 / conv3 各占 42% / 31%，且 ceil(96/64)=2 —— **两个最大的台阶只在"≤64"这个阈值上**。
  conv1 自己恒为 16,384（ceil(64/64)=1），但 conv2 的 cycle = c1·3·128，
  所以 c1 从 64 降到 32 直接砍掉 conv2 的一半。**conv1 是 cycle 的最大杠杆。**

结论：区间只改 conv1 下界（16 -> 32），其余沿用 zero_base —— 它们在 one_base 上没有被推翻。

======================================================================================
一个 E1b 没做到、本脚本要修正的方法论问题
======================================================================================
E1b 全程只看 **test**。test 一旦参与任何选择（排序、挑点、early stop），它就不再是
泛化估计，而变成了验证集 —— 报出来的数字会系统性偏乐观。

本脚本改成两段式：
    * 搜什么（Optuna 目标）-> 用 **val**（train_dataset 的 valid_indices 段，
      训练完全没见过、也没参与增强）
    * 最后报多少          -> 用 **test**，只在最后确认一次，不回流到搜索
两个数都写进 results.csv（fpr_val / fpr_test），随时能和 E1b 对照。

======================================================================================
判据 / 评估 / 模型构造全部复用 prunning.py
======================================================================================
刻意的：本脚本的 baseline 必须和 prunning.py 的 baseline 行逐位一致，
否则两张表没法放一起看。所以这里不重新实现 channel_importance / evaluate / 切片，
而是直接按文件路径加载 prunning.py。改那边的判据，这边立刻跟着变。
一致性校验：跑 prunning.py 记下 test 的 fpr/auc，再用
`--expect-fpr <v> --expect-auc <v>` 跑 --selftest，一致才算口径对齐。

======================================================================================
用法（全部在 one_base_prune/ 目录下执行）
======================================================================================
    # 0) 先跑 E4a 拿 one_base 的敏感度表和 baseline 参照值
    python prunning.py --device cuda
    # 1) 按新表改 SPACE 与 SEED_TRIALS，然后验链路
    python optuna_search.py --selftest --expect-fpr <v> --expect-auc <v>
    python optuna_search.py --smoke        # 3 trial × 1 epoch × 4096 条，约 1 分钟
    # 2) 正式搜
    python optuna_search.py --n-trials 40  # 目标默认 (cycles, auc_val)
    python optuna_search.py --n-trials 0 --polish-epochs 20  # 只给前沿补训练预算
    python optuna_search.py --report       # 不需要 optuna

产出（全部在 --out，默认 = 本文件所在目录）
    optuna_search.py    本脚本
    study.db            Optuna RDBStorage（SQLite）。**中断后原命令重跑即续**
    results.csv         每个 trial 一行，边跑边追加；--report 的数据源
    results.txt         对齐大表 + Pareto 前沿，可直接贴报告
    pareto.json         前沿成员（含完整通道配置，喂 ai8xize 补 cycle 用）
    manifest.json       搜索空间 / 目标 / 种子 / 库版本，出处可追溯
    ckpts/              只存"当刻进入前沿"的 trial 权重（剪枝是确定性的，其余可复现）
    polish.csv          补训练结果（--polish-epochs > 0 时）

======================================================================================
本脚本不测真实 cycle
======================================================================================
真 cycle 要跑 ai8xize，一个配置几分钟，塞进 Optuna 循环会把搜索慢 100 倍。
所以这里记两个**精确的**代理：
    macs        = Σ 每层 out×in×k×T（纯算术，可当算力目标）
    proc_passes = Σ ceil(每层 in / 64)
                  MAX78000 只有 64 个并行 conv 处理器，输入通道 >64 就得多走一遍。
                  基线是 2+1+2+2+1+1 = 9。
                  **conv3 的输入是 conv2 的输出：conv2 压到 ≤64，conv3 立刻少走一遍。**
                  （依据 ai8x-synthesis izer/load.py:106 `expand = c // in_expand_thresh`
                    与 load.py:260 `proc = ch % tc.dev.MAX_PROC`）
前沿只有几个点，跑完拿 pareto.json 里的通道配置去 ai8xize 补真 cycle 最省。
"""

import argparse
import csv
import json
import math
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 本文件原名 optuna.py。"python optuna.py" 会把所在目录塞进 sys.path[0]，
# 于是 `import optuna` 会 import 到脚本自己，症状：
#     AttributeError: module 'optuna' has no attribute 'logging'
# 改名为 optuna_search.py 之后这个坑从根上消失，不用再手删 sys.path。
# prunning.py 在同一个目录，用文件路径加载：不依赖 sys.path，也不会因为
# 目录改名而串味。
# ---------------------------------------------------------------------------
import importlib.util                                   # noqa: E402

_spec = importlib.util.spec_from_file_location("prunning", BASE_DIR / "prunning.py")
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)                             # 判据/评估/切片 的唯一真源


# --------------------------------------------------------------------------- #
# 搜索空间（数字出处见文件头的 E1b 表）
#   本表已按 **one_base 的 E4a 实测**重填（prune_e4a/results.csv，18 点）。
#   与 zero_base 相比只改了 conv1 的下界，理由见下面那行注释 —— 只改一处是刻意的：
#   其余区间在 one_base 上没有被推翻，保持不动才能和 zero_base 的 E1c 并排看。
# --------------------------------------------------------------------------- #
STEP = P.ROUND_TO                                       # 4：对齐 MAX78000 的 word packing
SPACE = {
    # ↓ zero_base 用 16。one_base 上 16ch 是唯一 val 与 test 同向恶化的点：
    #   val AUC 0.9961 -> 0.9943 (−0.0018)，val FPR 0.0126 -> 0.0281 (×2.2)
    #   test      0.9958 -> 0.9948 (−0.0010)，test FPR 0.0110 -> 0.0197 (×1.8)
    # 而 32ch 完全免费（val AUC −0.0001 / test +0.0008，双向都在噪声内）。
    # conv1 是 cycle 的最大杠杆：它自己 16,384 不变，但 conv2 的 cycle = c1·3·128，
    # 所以 c1 64->32 直接砍掉 conv2 一半（24,576 -> 12,288）。
    "conv1": (32, 64),
    "conv2": (24, 96),      # one_base E4a: 24ch -> AUC −0.0004 / FPR +0.0019/+0.0008，仍是最划算的一层
    "conv3": (24, 96),      # one_base E4a: 24ch -> AUC −0.0009(val)/+0.0005(test)，符号相反=噪声，留 24
    "conv4": (16, 64),      # one_base E4a: 16ch -> AUC −0.0008(val)/+0.0002(test)
    "conv5": (8, 32),       # one_base E4a: 8ch -> AUC ±0.0000，全场最便宜的维度
    "conv6": (4, 16),       # one_base E4a: 4ch -> AUC +0.0002(val)/+0.0006(test)，只省 408 B 但确实免费
}

# 用 E4a 已测过的点热身，避免 TPE 从零开始浪费前 12 个 trial（必须落在 SPACE 内）
SEED_TRIALS = [
    [64, 96, 96, 64, 32, 16],   # 不剪（对照组，E4a 的 baseline 就是它）
    [64, 64, 64, 64, 32, 16],   # 只跨 conv2/conv3 的 64 台阶 —— cycle −44.2%，权重 51,744 B
    [48, 64, 64, 48, 24, 16],   # 温和
    [32, 64, 64, 64, 32, 16],   # conv1 砍到 32（免费）+ 两个大台阶
    [32, 48, 48, 32, 16, 16],   # 均衡
    [32, 24, 96, 64, 32, 16],   # 只砍 conv1+conv2，保 conv3
    [64, 24, 32, 16, 8, 16],    # 保 conv1，其余压到底
    [32, 24, 32, 16, 8, 16],    # 极值点：10,784 B / 38,016 cycles（−67.9%），E4a 外推
]

# 目标名 -> results.csv 列名（顺序 = study 的 directions 顺序）
OBJ_COLUMN = {
    "cycles": "cycles_proc",
    "auc_val": "auc_val",
    "auc_test": "auc_test",
    "bytes": "weight_bytes",
    "fpr_val": "fpr_val",
    "fpr_test": "fpr_test",
    "macs": "macs",
    "passes": "proc_passes",
}
OBJ_DIRECTION = {
    "cycles": "minimize",
    "macs": "minimize",
    "passes": "minimize",
    "bytes": "minimize",
    "fpr_val": "minimize",
    "fpr_test": "minimize",
    "auc_val": "maximize",
    "auc_test": "maximize",
}
# 修正后的正式目标：硬件 cycle 轴 + 低噪声精度轴。
#   * 不用 bytes：MAX78000 权重预算约 442 KB，本模型只占 1.5%~18%，内存从来不是瓶颈
#   * 不用 fpr_val 当目标：val/test 有 +0.003 系统偏差、sd 0.0045；
#     AUC 的偏差只有 +0.0002、sd 0.0008（紧 5.6 倍）。FPR 退回"报告指标"。
DEFAULT_OBJECTIVES = ["cycles", "auc_val"]
_REPORT_OBJECTIVES = list(DEFAULT_OBJECTIVES)     # append_row 每次刷新 results.txt 时用

FIELDS = [
    "run_id", "trial", "ts", "state",
    "ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "fc_in",
    "weight_bytes", "d_weight_bytes", "macs", "proc_passes", "cycles_proc",
    "fpr_val", "tpr_val", "auc_val",
    "fpr_test", "tpr_test", "auc_test", "top1_test",
    "ft_epochs", "lr", "seed", "seconds", "ckpt",
]


# --------------------------------------------------------------------------- #
# 硬件代理指标（精确算术，不是猜测）
# --------------------------------------------------------------------------- #
def arch_macs(ch):
    """Σ 每层 out*in*k*T。T 是池化后的时间长度。

    输入 128 帧。池化只出现在 conv2/3/5/6（models/sentinel.py）：
    conv1 T=128（无池化）→ conv2 T=128 再池化成 64 → conv3 64 再池化成 32
    → conv4 T=32（无池化）→ conv5 32 再池化成 16 → conv6 T=16 再 pool16 成 1。
    （自检：128/2/2/2/16 = 1，与 sentinel.py 的注释一致）
    """
    c1, c2, c3, c4, c5, c6 = ch
    return (c1 * 128 * 1 * 128
            + c2 * c1 * 3 * 128
            + c3 * c2 * 3 * 64
            + c4 * c3 * 3 * 32
            + c5 * c4 * 3 * 32
            + c6 * c5 * 1 * 16
            + c6 * 2)


def arch_proc_passes(ch):
    """Σ ceil(in/64)。MAX78000 只有 64 个并行卷积处理器，输入通道 >64 要多走一遍。

    基线 (64,96,96,64,32,16): conv1 in=128 -> 2，conv3 in=96 -> 2，conv4 in=96 -> 2，
    其余 1，合计 9。把 conv2 压到 ≤64 就能让 conv3 从 2 变 1 —— 这是整个搜索里
    唯一一个**离散的**大台阶，比省几 KB 重要。
    """
    ins = [128, ch[0], ch[1], ch[2], ch[3], ch[4]]
    return sum(math.ceil(i / 64) for i in ins)


def arch_cycles(ch):
    """一阶 cycle 模型：Σ ceil(out/64) · in · k · T。

    依据 izer/backend/max7800x.py:454 `out_expand = ceil(out/MAX_PROC)`：
    输出通道超过 64 就要多用一轮处理器。每轮里，一个处理器负责一个输出通道，
    串行遍历 in × k × T。所以

        cycles_layer ≈ out_expand × (in × k × T)

    **in_expand（= ceil(in/64)）不出现**：它把输入通道分成若干趟，每趟只算 1/in_expand
    的输入，总工作量不变，乘进去再除出来正好抵消。之前把它当 cycle 代理是错的。

    重要推论：cycle 由**输入侧** in·k·T 决定，把输出通道压到 64 以下之后就没有并行度
    可捡了 —— 这解释了为什么 12 KB → 6.5 KB 权重再砍 46%，cycle 只降 17%。

    **这是推导值，没有 ai8xize 实测背书。** 真实估算在 izer/cycles.py，本脚本没调用它，
    因为跑 ai8xize 需要先量化（QAT/quantize 产 int8 ckpt）并为每个通道配置写 YAML。
    方向可信，绝对值不可信。
    """
    c = list(ch)
    T = [128, 128, 64, 32, 32, 16]      # 各层卷积时的时间长度（池化前）
    K = [1, 3, 3, 3, 3, 1]
    ins = [128, c[0], c[1], c[2], c[3], c[4]]
    return sum(math.ceil(c[i] / 64) * ins[i] * K[i] * T[i] for i in range(6))


# --------------------------------------------------------------------------- #
# 剪枝（复用 prunning.py 的切片原语，保证与 E1b 逐位一致）
# --------------------------------------------------------------------------- #
def prune_to(model, layer_name, keep_n):
    """把 layer_name 的输出通道剪到 keep_n 个，并同步下游输入通道。

    与 P.prune_layer 的区别：那个收 ratio 再反推通道数（有 float 往返），这里直接给
    通道数。重要性判据完全相同（P.channel_importance，即 torch_pruning 的 p=2/mean）。
    """
    idx = P.CHAIN.index(layer_name)
    layer = getattr(model, layer_name)
    cur = int(layer.op.weight.shape[0])
    keep_n = max(STEP, (int(keep_n) // STEP) * STEP)
    if keep_n >= cur:
        return cur                                    # 不减反增不可能，直接不动

    imp = P.channel_importance(layer.op.weight.data)
    keep = torch.sort(torch.topk(imp, keep_n).indices).values
    P._slice_out(layer.op, keep)                              # 剪自己 out
    P._slice_in(getattr(model, P.CHAIN[idx + 1]).op, keep)    # 同步下游 in
    return keep_n


def _as_dict(channels):
    """通道配置既接受 {conv1: n, ...}，也接受 [n1..n6]（按 conv1..conv6 顺序）。"""
    if isinstance(channels, dict):
        return channels
    seq = list(channels)
    if len(seq) != len(SPACE):
        raise ValueError(f"通道配置需要 {len(SPACE)} 个数，收到 {len(seq)}: {seq}")
    return {name: seq[i] for i, name in enumerate(SPACE)}


def build_pruned(channels, device):
    """从基线 ckpt 起，按 conv1 -> conv6 顺序剪到目标通道数。

    顺序必须从浅到深：剪 conv_k 会改掉 conv_{k+1} 的输入通道，之后剪 conv_{k+1} 时
    它的重要性判据是**在已缩窄的输入上**重算的，这是对的。
    """
    channels = _as_dict(channels)
    model, _ = P.build_model(device)
    for name in P.PRUNABLE:
        prune_to(model, name, channels[name])
    got = P.channel_tuple(model)
    if got[6] != got[5]:                               # 纯链式下必然相等，留作自检
        raise RuntimeError(f"依赖同步失败: {got}")
    return model


# --------------------------------------------------------------------------- #
# 训练 / 评估
# --------------------------------------------------------------------------- #
def train_epochs(model, loader, device, epochs, lr):
    """短微调。配方沿用 E1b/基线：Adam 常数 lr + CrossEntropy + weight_decay 1e-4。

    没有 early stop：Optuna 的多目标 study 不支持 trial.report/should_prune
    （trial/_trial.py:481 直接 raise NotImplementedError），所以每个 trial 都跑满。
    """
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    losses = []
    for _ in range(epochs):
        loss_sum = 0.0
        total = 0
        for inputs, labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(inputs), labels)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * labels.size(0)
            total += labels.size(0)
        losses.append(loss_sum / max(total, 1))
    model.eval()
    return losses


@torch.no_grad()
def eval_both(model, val_loader, test_loader, device):
    """val 用来选（干净），test 用来报（最后确认）。见文件头的方法论说明。"""
    return P.evaluate(model, val_loader, device), P.evaluate(model, test_loader, device)


def _worst_if_nan(x):
    """val 上连 TPR=0.95 都到不了时 fpr 是 nan。Optuna 不接受 nan。"""
    if x is None:
        return 1.0
    x = float(x)
    return 1.0 if math.isnan(x) else x


# 参照值（可选）。E1c 时代这里是写死的 zero_base 值（0.011809 / 0.996197），
# 换到 one_base 就会一直报「不一致」。现在改成由 --expect-fpr/--expect-auc 传入：
# 先跑 prunning.py 拿到 one_base 的 baseline 行，再把那两个数抄进命令。
EXPECT = {"fpr": None, "auc": None}


def _check_ref(bt):
    """把当前 baseline 与 --expect-* 比对。没给参照值就明确说"跳过"，不假装通过。

    容差 2e-5 而不是 1e-6：同一份权重在不同设备上跑，AUC 的第 6 位会差 1（cuda vs cpu
    的浮点累加顺序不同）。E4a 在 cuda 上量的是 0.995824，cpu 上复现出 0.995823，
    两者是同一个模型。用 1e-6 会每次跨设备比对都误报。FPR 不受影响（完全一致）。
    """
    if EXPECT["fpr"] is None or EXPECT["auc"] is None:
        return "（未给 --expect-fpr/--expect-auc，跳过与 E1b 的比对）"
    same = (abs(bt["fpr_at"] - EXPECT["fpr"]) < 2e-5
            and abs(bt["auc"] - EXPECT["auc"]) < 2e-5)
    return (f"参照 E1b: {EXPECT['fpr']:.6f} / {EXPECT['auc']:.6f}  "
            + ("一致 ✔ 口径对齐" if same else "**不一致，先查环境/ckpt**"))


# --------------------------------------------------------------------------- #
# CSV / 报告
# --------------------------------------------------------------------------- #
def read_rows(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_row(csv_path, row):
    """立刻落盘 + 每点重写 results.txt。进程被硬杀也不会只剩半张表。"""
    csv_path = Path(csv_path)
    new_file = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDS})
        f.flush()
    csv_path.with_name("results.txt").write_text(
        format_report(read_rows(csv_path), _REPORT_OBJECTIVES) + "\n", encoding="utf-8")


def pareto_front(rows, obj_names):
    """非支配解集。obj_names 是目标名，按 OBJ_DIRECTION 归一化成"越小越好"。"""
    vecs = []
    for r in rows:
        if r.get("state") != "complete":
            continue
        try:
            v = tuple(_obj_value(r, o) for o in obj_names)
        except (TypeError, ValueError):
            continue
        if any(math.isnan(x) for x in v):
            continue
        vecs.append((v, r))
    front = []
    for v, r in vecs:
        dominated = any(
            all(a <= b for a, b in zip(w, v)) and any(a < b for a, b in zip(w, v))
            for w, _ in vecs)
        if not dominated:
            front.append(r)
    return front


def _num(r, key, default=0.0, cast=float):
    v = r.get(key)
    if v is None or v == "":
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(f) else cast(f)


def _obj_value(r, name, default=float("nan")):
    """把某个目标按方向归一化成"越小越好"：maximize 的取负。"""
    v = _num(r, OBJ_COLUMN[name], default=default)
    return -v if OBJ_DIRECTION[name] == "maximize" else v


def _fmt_row(r, base_w, base_cyc, base_fpr):
    ch = "/".join(r.get(f"ch{i}", "") or "?" for i in range(1, 7))
    w = _num(r, "weight_bytes")
    c = _num(r, "cycles_proc")
    dcyc = "—" if (not c or not base_cyc) else f"{c / base_cyc - 1:+.1%}"
    line = (f"{str(r.get('trial', '')):>5s} {str(r.get('state', '')):<8s} "
            f"{ch:>22s} {int(w):8d} {int(w) - base_w:+8d} "
            f"{int(c):8d} {dcyc:>8s} {_num(r, 'macs'):9.0f} ")
    for key in ("auc_val", "auc_test"):
        v = _num(r, key, default=float("nan"))
        line += f"{'—':>8s} " if math.isnan(v) else f"{v:8.5f} "
    for key in ("fpr_val", "fpr_test"):
        v = _num(r, key, default=float("nan"))
        line += f"{'—':>9s} " if math.isnan(v) else f"{v:9.4f} "
    fv = _num(r, "fpr_val", default=float("nan"))
    line += f"{'—':>8s} " if math.isnan(fv) else f"{fv - base_fpr:+8.4f} "
    line += f"{_num(r, 'seconds'):6.0f}s"
    return line


def format_report(rows, obj_names):
    if not rows:
        return "没有数据。"
    base = next((r for r in rows if r.get("trial") == "-1"), None)
    base_w = int(_num(base, "weight_bytes")) if base else 0
    base_cyc = _num(base, "cycles_proc") if base else 0.0
    base_fpr = _num(base, "fpr_val", default=float("nan")) if base else float("nan")

    front = pareto_front(rows, obj_names)
    front_ids = {r.get("trial") for r in front}
    cyc_key = "cycles_proc" if "cycles" in obj_names else "weight_bytes"

    head = (f"{'trial':>5s} {'state':<8s} {'ch1..ch6':>22s} {'bytes':>8s} {'dW':>8s} "
            f"{'cycles':>8s} {'dCyc':>8s} {'macs':>9s} {'auc_val':>8s} {'auc_test':>8s} "
            f"{'fpr_val':>9s} {'fpr_test':>9s} {'dFPR':>8s} {'sec':>7s}")
    sep = "-" * len(head)

    lines = [f"目标: " + ", ".join(f"{o}({OBJ_DIRECTION[o]})" for o in obj_names),
             sep, head, sep]
    ordered = sorted(rows, key=lambda r: (r.get("state") != "complete", _num(r, "weight_bytes")))
    for r in ordered:
        lines.append(("*" if r.get("trial") in front_ids else " ")
                     + _fmt_row(r, base_w, base_cyc, base_fpr))

    lines += ["", f"=== Pareto 前沿（{len(front)} 个非支配解，按 {cyc_key} 升序）===",
              sep, head, sep]
    for r in sorted(front, key=lambda r: _num(r, cyc_key)):
        lines.append("*" + _fmt_row(r, base_w, base_cyc, base_fpr))
    lines += ["",
              "* = 在 Pareto 前沿上。dFPR 相对 trial -1（不剪、不微调）的 **val** 变化。",
              "cycles = Σ ceil(out/64)·in·k·T 的一阶模型（基线值由 trial -1 给出）。",
              "         推导自 izer/backend/max7800x.py 的 out_expand；**未经 ai8xize 实测**，",
              "         方向可信、绝对值不可信。真实值需先量化再跑 ai8xize。",
              "macs 仅作参考：cycle 由输入侧 in·k·T 决定，macs 不是 cycle 的线性代理。"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 一次完整评估（Optuna objective 与 --polish 共用同一条路径）
# --------------------------------------------------------------------------- #
def run_one(channels, epochs, lr, seed, device, loaders):
    torch.manual_seed(seed)
    np.random.seed(seed)

    t0 = time.time()
    model = build_pruned(channels, device)
    got = P.channel_tuple(model)
    bytes_ = P.weight_bytes(model)

    train_loader, val_loader, test_loader = loaders
    losses = train_epochs(model, train_loader, device, epochs, lr)
    v, t = eval_both(model, val_loader, test_loader, device)

    return model, dict(
        channels=got,
        weight_bytes=bytes_,
        macs=arch_macs(got[:6]),
        proc_passes=arch_proc_passes(got[:6]),
        cycles_proc=arch_cycles(got[:6]),
        fpr_val=_worst_if_nan(v["fpr_at"]),
        tpr_val=v["tpr_at"],
        auc_val=v["auc"],
        fpr_test=_worst_if_nan(t["fpr_at"]),
        tpr_test=t["tpr_at"],
        auc_test=t["auc"],
        top1_test=t["top1"],
        train_loss=losses[-1] if losses else float("nan"),
        seconds=time.time() - t0,
    )


# --------------------------------------------------------------------------- #
# 数据
# --------------------------------------------------------------------------- #
def make_loaders(limit, batch):
    """train 用训练段（带增强）；val 用 train_dataset 的 valid_indices 段（干净）；
    test 用 test_dataset。limit>0 时等间距抽样，保持正负比。"""
    train_ds, test_ds = P.sentinel_get_datasets(data=None, load_train=True, load_test=True)
    n_train = train_ds.valid_indices.start

    tr_idx = list(range(n_train))
    va_idx = list(train_ds.valid_indices)
    te_idx = list(range(len(test_ds)))
    if limit:
        def stride(n):
            return list(range(0, n, max(1, n // limit)))[:limit]
        tr_idx = stride(n_train)
        te_idx = stride(len(test_ds))
        va_idx = va_idx[::max(1, len(va_idx) // limit)][:limit]

    train_loader = DataLoader(Subset(train_ds, tr_idx), batch_size=batch, shuffle=True,
                              num_workers=0, drop_last=True)
    val_loader = DataLoader(Subset(train_ds, va_idx), batch_size=batch, shuffle=False,
                            num_workers=0)
    test_loader = DataLoader(Subset(test_ds, te_idx), batch_size=batch, shuffle=False,
                             num_workers=0)
    print(f"train {len(tr_idx)} / val {len(va_idx)} / test {len(te_idx)}")
    return train_loader, val_loader, test_loader


# --------------------------------------------------------------------------- #
# 前置检查
# --------------------------------------------------------------------------- #
def require_optuna():
    try:
        import optuna
    except ImportError:
        sys.exit(
            "\n[缺依赖] 当前解释器里没有 optuna：\n"
            f"    {sys.executable}\n\n"
            "装它（二选一，但先看下面的提醒）：\n"
            f'    "{sys.executable}" -m pip install optuna\n\n'
            "提醒：E1b 的基线（AUC 0.996197 / FPR95 0.011809）是在 **ai8x** 环境量的\n"
            "（numpy 1.26.4 / sklearn 1.9.1）。ai-train 是 numpy 2.4.6 / sklearn 1.8.0，\n"
            "数值可能有微小漂移，那样两张表就不能逐位对齐。要让 E1c 与 E1b 可比，\n"
            "建议装进 ai8x 环境。\n"
        )
    import optuna.logging                  # optuna 5.x 的顶层不再预载这个子模块
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    return optuna


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    global _REPORT_OBJECTIVES

    ap = argparse.ArgumentParser(
        description="E1c: Optuna 多目标剪枝搜索（bytes vs FPR@TPR=0.95）",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)

    ap.add_argument("--n-trials", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=0, help="秒；0 = 不限")
    ap.add_argument("--ft-epochs", type=int, default=12,
                    help="每 trial 微调 epoch。默认 12（配 lr 3e-4）。"
                         "E1b 用的是 5ep/lr 1e-3，实测在激进端压低了 AUC 0.0015、"
                         "FPR 0.003，会系统性把前沿推向保守")
    ap.add_argument("--lr", type=float, default=3e-4,
                    help="默认 3e-4；1e-3 对这个已收敛的基线偏大（不剪枝只多训 5ep 都会变差）")
    ap.add_argument("--seed", type=int, default=0)

    ap.add_argument("--objectives", nargs="+", default=DEFAULT_OBJECTIVES,
                    choices=list(OBJ_COLUMN),
                    help=f"可多选: {', '.join(OBJ_COLUMN)}。默认 {' '.join(DEFAULT_OBJECTIVES)}")
    ap.add_argument("--sampler", default="tpe", choices=["tpe", "random"])
    ap.add_argument("--no-seed-trials", dest="seed_trials", action="store_false")

    ap.add_argument("--polish-epochs", type=int, default=0,
                    help=">0 时：给前沿成员补足训练预算重跑一遍，抵消"
                         "「激进配置需要更多 epoch」带来的系统性偏差")
    ap.add_argument("--polish-top", type=int, default=6)

    ap.add_argument("--device", default="cpu", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--batch", type=int, default=P.BATCH)
    ap.add_argument("--limit", type=int, default=0, help="只调试用：等间距抽样这么多条")
    ap.add_argument("--out", default=".", help="产出目录（默认 = 本脚本所在目录）")

    ap.add_argument("--storage", default="study.db")
    ap.add_argument("--study-name", default="e4_pareto")
    ap.add_argument("--ckpt", default=None,
                    help="换基线：指向任意 .pth.tar（默认 = prunning.py 里的 one_base）")
    ap.add_argument("--expect-fpr", type=float, default=None,
                    help="与 prunning.py 的 baseline 行做逐位比对（test FPR@TPR95）")
    ap.add_argument("--expect-auc", type=float, default=None,
                    help="与 prunning.py 的 baseline 行做逐位比对（test AUC）")
    ap.add_argument("--report", action="store_true", help="只读 results.csv 出表，不需要 optuna")
    ap.add_argument("--selftest", action="store_true", help="验链路，不需要 optuna，不训练")
    ap.add_argument("--smoke", action="store_true", help="3 trial × 1 epoch × 4096 条")
    ap.add_argument("--reset", action="store_true", help="删掉 study.db / results.csv / ckpts")
    ap.add_argument("--yes", action="store_true", help="配合 --reset 确认删除")
    args = ap.parse_args()

    if args.ckpt:
        P.set_checkpoint(args.ckpt)
    EXPECT["fpr"], EXPECT["auc"] = args.expect_fpr, args.expect_auc

    if isinstance(args.objectives, str):
        args.objectives = args.objectives.split(",")
    _REPORT_OBJECTIVES = list(args.objectives)
    if "fpr_test" in args.objectives:
        print("[警告] 用 fpr_test 当目标 = 让 test 参与选择，报出来的数会偏乐观。")

    out_dir = (BASE_DIR / args.out).resolve()
    csv_path = out_dir / "results.csv"

    if args.report:
        print(format_report(read_rows(csv_path), args.objectives))
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir = out_dir / "ckpts"
    db_path = out_dir / args.storage

    if args.reset:
        targets = [db_path, csv_path, out_dir / "results.txt", out_dir / "pareto.json",
                   out_dir / "manifest.json", out_dir / "polish.csv"]
        print("[reset] 即将删除:")
        for t in targets:
            print("   ", t, "(存在)" if t.exists() else "(不存在)")
        print("   ", ckpt_dir, "(整个目录)")
        if not args.yes:
            sys.exit("\n拒绝执行：加 --yes 确认。")
        for t in targets:
            if t.exists():
                t.unlink()
        if ckpt_dir.is_dir():
            for f in ckpt_dir.glob("*"):
                f.unlink()
            ckpt_dir.rmdir()
        print("[reset] 完成")
        return

    if args.smoke:
        args.n_trials, args.ft_epochs, args.limit = 3, 1, 4096
        print("[smoke] n_trials=3 ft_epochs=1 limit=4096")

    # ---- 设备 ----
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cpu":
        torch.set_num_threads(args.threads)
        print(f"device = cpu   torch threads = {args.threads}   （GPU 未使用）")
    else:
        print(f"device = {device}")

    ckpt_dir.mkdir(exist_ok=True)
    loaders = make_loaders(args.limit, args.batch)

    # ---- selftest：不需要 optuna ----
    if args.selftest:
        print("\n[selftest] 验 3 个通道配置的形状 / 代理指标 / 评估链路（不训练）")
        base_model, _ = P.build_model(device)
        bv, bt = eval_both(base_model, loaders[1], loaders[2], device)
        print(f"  基线 {P.channel_tuple(base_model)}  bytes={P.weight_bytes(base_model)}  "
              f"macs={arch_macs(P.channel_tuple(base_model)[:6])}  "
              f"passes={arch_proc_passes(P.channel_tuple(base_model)[:6])}")
        print(f"  test  fpr={bt['fpr_at']:.6f}  auc={bt['auc']:.6f}  top1={bt['top1']:.4f}"
              f"   {_check_ref(bt)}")
        print(f"  val   fpr={bv['fpr_at']:.6f}  auc={bv['auc']:.6f}")
        del base_model
        for ch in ([32, 48, 24, 48, 16, 16], [16, 24, 24, 16, 8, 4]):
            model = build_pruned(ch, device)
            got = P.channel_tuple(model)
            with torch.no_grad():
                out = model(torch.randn(*P.INPUT_SHAPE, device=device))
            v, t = eval_both(model, loaders[1], loaders[2], device)
            print(f"  req {ch} -> got {got}  out {tuple(out.shape)}  "
                  f"bytes {P.weight_bytes(model)}  macs {arch_macs(got[:6])}  "
                  f"passes {arch_proc_passes(got[:6])}  "
                  f"val_fpr {v['fpr_at']:.4f}  test_fpr {t['fpr_at']:.4f}")
            del model
        print("\n[selftest] 通过 -> 装 optuna 后可以正式跑。")
        return

    optuna = require_optuna()

    # ---- baseline（trial -1）：不剪、不微调。必须与 E1b 的 baseline 逐位一致 ----
    base_model, _ = P.build_model(device)
    bv, bt = eval_both(base_model, loaders[1], loaders[2], device)
    base_bytes = P.weight_bytes(base_model)
    base_ch = P.channel_tuple(base_model)
    print(f"\n[baseline] bytes={base_bytes}  cycles={arch_cycles(base_ch[:6])}  "
          f"channels={base_ch}\n"
          f"           val_fpr={bv['fpr_at']:.4f}  test_fpr={bt['fpr_at']:.4f}  "
          f"auc_test={bt['auc']:.6f}")
    if args.limit:
        print("           （--limit 抽样模式，不做与 E1b 的比对）")
    else:
        print("           " + _check_ref(bt))
    del base_model

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not read_rows(csv_path):
        append_row(csv_path, dict(
            run_id=run_id, trial="-1", ts=datetime.now().isoformat(timespec="seconds"),
            state="baseline",
            **{f"ch{i + 1}": base_ch[i] for i in range(6)}, fc_in=base_ch[6],
            weight_bytes=base_bytes, d_weight_bytes=0,
            macs=arch_macs(base_ch[:6]), proc_passes=arch_proc_passes(base_ch[:6]),
            cycles_proc=arch_cycles(base_ch[:6]),
            fpr_val=f"{bv['fpr_at']:.6f}", tpr_val=f"{bv['tpr_at']:.6f}",
            auc_val=f"{bv['auc']:.6f}",
            fpr_test=f"{bt['fpr_at']:.6f}", tpr_test=f"{bt['tpr_at']:.6f}",
            auc_test=f"{bt['auc']:.6f}", top1_test=f"{bt['top1']:.4f}",
            ft_epochs=0, lr=args.lr, seed=args.seed, seconds="0", ckpt=""))

    # ---- manifest ----
    manifest = dict(
        run_id=run_id,
        checkpoint=str(P.LOG_DIR / P.CKPT_NAME),
        input_shape=list(P.INPUT_SHAPE),
        base_channels=list(P.BASE_CHANNELS),
        step=STEP,
        search_space={k: {"low": v[0], "high": v[1],
                          "allowed": list(range(v[0], v[1] + 1, STEP))}
                      for k, v in SPACE.items()},
        objectives=args.objectives,
        directions={o: OBJ_DIRECTION[o] for o in args.objectives},
        ft_epochs=args.ft_epochs, lr=args.lr, seed=args.seed,
        sampler=args.sampler,
        seed_trials=SEED_TRIALS if args.seed_trials else [],
        baseline=dict(channels=list(base_ch), bytes=base_bytes,
                      cycles_proc=arch_cycles(base_ch[:6]),
                      val_fpr=bv["fpr_at"], test_fpr=bt["fpr_at"], auc_test=bt["auc"]),
        prior="one_base E4a 单层敏感度（prune_e4a/results.csv, 18 点, 5ep/lr1e-3）。"
              "只改 conv1 下界 16->32；dFPR 的 val/test 符号仅 8/18 一致 -> 只把 AUC 当排序轴",
        versions=dict(python=sys.version.split()[0], torch=torch.__version__,
                      numpy=np.__version__,
                      sklearn=__import__("sklearn").__version__,
                      optuna=optuna.__version__),
        started=datetime.now().isoformat(timespec="seconds"),
        note="目标 = (cycles 一阶模型, AUC val)。FPR@TPR95 / TPR@FPR1% 只在 test 上报告，"
             "不参与选择。cycles 未经 ai8xize 实测，方向可信、绝对值不可信。",
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- study ----
    sampler = (optuna.samplers.RandomSampler(seed=args.seed) if args.sampler == "random"
               else optuna.samplers.TPESampler(seed=args.seed, multivariate=True,
                                               n_startup_trials=12))
    # 不加 pruner：多目标 study 不支持 trial.report，Optuna 直接 raise NotImplementedError。
    study = optuna.create_study(
        study_name=args.study_name, storage=f"sqlite:///{db_path.as_posix()}",
        load_if_exists=True, directions=[OBJ_DIRECTION[o] for o in args.objectives],
        sampler=sampler)

    if args.seed_trials and len(study.trials) == 0:
        for ch in SEED_TRIALS:
            study.enqueue_trial({f"conv{i + 1}": ch[i] for i in range(6)}, skip_if_exists=True)
        print(f"[warmup] 已排入 {len(SEED_TRIALS)} 个 E1b 已测过的种子点")

    n_done = len([t for t in study.trials if t.state.name == "COMPLETE"])
    print(f"study '{args.study_name}'  已完成 {n_done} 个 trial  -> {db_path}")

    # ---- frontier tracker：只有"当刻非支配"的点才落 ckpt ----
    tracker = {"pts": []}

    def enters_front(vec):
        for w in tracker["pts"]:
            if all(a <= b for a, b in zip(w, vec)) and any(a < b for a, b in zip(w, vec)):
                return False
        return True

    def objective(trial):
        channels = {name: trial.suggest_int(name, lo, hi, step=STEP)
                    for name, (lo, hi) in SPACE.items()}
        trial_seed = args.seed * 100000 + trial.number
        print(f"\n--- trial {trial.number}: {[channels[k] for k in SPACE]} "
              f"(seed {trial_seed}) ---")

        try:
            model, m = run_one([channels[k] for k in SPACE], args.ft_epochs,
                               args.lr, trial_seed, device, loaders)
        except Exception:
            traceback.print_exc()
            append_row(csv_path, dict(
                run_id=run_id, trial=trial.number,
                ts=datetime.now().isoformat(timespec="seconds"), state="failed",
                **{f"ch{i + 1}": channels[f"conv{i + 1}"] for i in range(6)}))
            raise optuna.TrialPruned()        # 记成 pruned，别让坏点污染前沿

        vec = tuple(_obj_value(m, o) for o in args.objectives)   # 归一化成越小越好
        ckpt_name = ""
        if enters_front(vec):
            ckpt_name = f"trial_{trial.number:04d}.pth.tar"
            try:
                torch.save({"state_dict": model.state_dict(),
                            "channels": list(m["channels"][:6]),
                            "metrics": m, "run_id": run_id, "trial": trial.number},
                           ckpt_dir / ckpt_name)
            except OSError as exc:      # 磁盘问题不该杀掉整轮搜索
                print(f"    [警告] 存 ckpt 失败，忽略: {exc}")
                ckpt_name = ""
            tracker["pts"].append(vec)
        del model

        append_row(csv_path, dict(
            run_id=run_id, trial=trial.number,
            ts=datetime.now().isoformat(timespec="seconds"), state="complete",
            **{f"ch{i + 1}": m["channels"][i] for i in range(6)}, fc_in=m["channels"][6],
            weight_bytes=m["weight_bytes"], d_weight_bytes=m["weight_bytes"] - base_bytes,
            macs=m["macs"], proc_passes=m["proc_passes"], cycles_proc=m["cycles_proc"],
            fpr_val=f"{m['fpr_val']:.6f}", tpr_val=f"{m['tpr_val']:.6f}",
            auc_val=f"{m['auc_val']:.6f}",
            fpr_test=f"{m['fpr_test']:.6f}", tpr_test=f"{m['tpr_test']:.6f}",
            auc_test=f"{m['auc_test']:.6f}", top1_test=f"{m['top1_test']:.4f}",
            ft_epochs=args.ft_epochs, lr=args.lr, seed=trial_seed,
            seconds=f"{m['seconds']:.1f}", ckpt=ckpt_name))

        print(f"    bytes={m['weight_bytes']} ({m['weight_bytes'] - base_bytes:+d})  "
              f"cycles={m['cycles_proc']}  auc_val={m['auc_val']:.5f}  "
              f"fpr_test={m['fpr_test']:.4f}  {m['seconds']:.0f}s"
              + ("  *前沿" if ckpt_name else ""))
        # 注意：vec 是按方向归一化过的（maximize 取负），只能给 enters_front 用。
        # 返回给 Optuna 的必须是原始值，方向由 study 的 directions 负责。
        return [float(m[OBJ_COLUMN[o]]) for o in args.objectives]

    if args.n_trials > 0:
        study.optimize(objective, n_trials=args.n_trials,
                       timeout=args.timeout or None, n_jobs=1, show_progress_bar=False)

    # ---- polish：给前沿成员补足训练预算 ----
    if args.polish_epochs > 0:
        rows = read_rows(csv_path)
        front = pareto_front(rows, args.objectives)
        front = sorted(front, key=lambda r: _num(r, "cycles_proc"))[:args.polish_top]
        print(f"\n[polish] {len(front)} 个前沿成员，每个补到 {args.polish_epochs} epoch")
        polish_csv = out_dir / "polish.csv"
        for r in front:
            ch = [int(_num(r, f"ch{i}")) for i in range(1, 7)]
            print(f"  polish trial {r['trial']}: {ch}")
            _, m = run_one(ch, args.polish_epochs, args.lr, int(_num(r, "seed")), device, loaders)
            append_row(polish_csv, {
                "run_id": run_id, "trial": r["trial"],
                "ts": datetime.now().isoformat(timespec="seconds"), "state": "polished",
                **{f"ch{i + 1}": m["channels"][i] for i in range(6)}, "fc_in": m["channels"][6],
                "weight_bytes": m["weight_bytes"],
                "d_weight_bytes": m["weight_bytes"] - base_bytes,
                "macs": m["macs"], "proc_passes": m["proc_passes"],
                "cycles_proc": m["cycles_proc"],
                "fpr_val": f"{m['fpr_val']:.6f}", "tpr_val": f"{m['tpr_val']:.6f}",
                "auc_val": f"{m['auc_val']:.6f}",
                "fpr_test": f"{m['fpr_test']:.6f}", "tpr_test": f"{m['tpr_test']:.6f}",
                "auc_test": f"{m['auc_test']:.6f}", "top1_test": f"{m['top1_test']:.4f}",
                "ft_epochs": args.polish_epochs, "lr": args.lr, "seed": r["seed"],
                "seconds": f"{m['seconds']:.1f}", "ckpt": ""})
            print(f"    val_fpr={m['fpr_val']:.4f}  test_fpr={m['fpr_test']:.4f}")

    # ---- 收尾 ----
    rows = read_rows(csv_path)
    front = pareto_front(rows, args.objectives)
    pareto = []
    for r in sorted(front, key=lambda r: _num(r, "cycles_proc")):
        item = {"trial": int(_num(r, "trial")),
                "cycles_proc": int(_num(r, "cycles_proc")),
                "weight_bytes": int(_num(r, "weight_bytes")),
                "macs": int(_num(r, "macs")),
                "proc_passes": int(_num(r, "proc_passes")),
                "auc_val": _num(r, "auc_val"),
                "auc_test": _num(r, "auc_test"),
                "fpr_val": _num(r, "fpr_val"),
                "fpr_test": _num(r, "fpr_test"),
                "tpr_test": _num(r, "tpr_test"),
                "ckpt": r.get("ckpt", "")}
        # 键名直接用搜索空间的层名，可以原样喂给 build_pruned()
        item.update({f"conv{i + 1}": int(_num(r, f"ch{i + 1}")) for i in range(6)})
        pareto.append(item)
    (out_dir / "pareto.json").write_text(json.dumps(
        {"objectives": args.objectives, "baseline": manifest["baseline"], "front": pareto},
        ensure_ascii=False, indent=2), encoding="utf-8")

    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    manifest["n_trials_in_study"] = len(study.trials)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = format_report(rows, args.objectives)
    (out_dir / "results.txt").write_text(report + "\n", encoding="utf-8")
    print("\n" + report)
    print(f"\n已写: {csv_path}")
    print(f"已写: {out_dir / 'results.txt'}")
    print(f"已写: {out_dir / 'pareto.json'}")
    print(f"已写: {out_dir / 'manifest.json'}")
    print(f"已写: {db_path}")
    print(f"已存: {ckpt_dir}\\*.pth.tar  ({len(list(ckpt_dir.glob('*.pth.tar')))} 个前沿点)")


if __name__ == "__main__":
    main()
