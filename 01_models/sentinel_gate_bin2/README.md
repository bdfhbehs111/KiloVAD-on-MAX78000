# 极简哨兵（sentinel_tiny）

> MAX78000 声学哨兵的**浅层门控模型**（判断正常/异常）：从 7 万参数压到 **2,003 参数**
> 打包日期：2026-10-08

## 性能对比

| 项 | 现役哨兵（kws20 前 4 层） | **极简哨兵（本模型）** | 变化 |
|---|---|---|---|
| **参数量** | 69,556 | **2,003** | **↓ 35 倍** |
| **weights.h** | ~70 KB | **10.2 KB** | ↓ 7 倍 |
| **baseline 区分度** | 5.74 | **5.19** | 仅降 10% |
| ESC-50 二分类准确率 | — | 80.4% | — |
| 结构来源 | kws20 浅层（未为任务训练） | **专门训练 + DrongoNet 风格** | — |

## 目录结构

```
sentinel_tiny/
├── weights/                          # 模型本体
│   ├── sentinel_tiny_b2087.pth.tar       PyTorch 权重（2,087 含频率强调层）
│   ├── sentinel_tiny_ai8x.pth.tar        ai8x 格式（2,003，频率强调已折叠）
│   └── sentinel_tiny_ai8x_q8.pth.tar     量化 8bit ← 上板用
│
├── code/                             # 必要代码
│   ├── tiny_sentinel.py                  训练 + 评测（含 DrongoNet 风格设计）
│   └── export_ai8x.py                    权重迁移（含 FreqEmphasis 折叠）
│
└── max78000/                         # 上板固件
    ├── sentinel_tiny-hwc.yaml            网络描述
    ├── sample_sentinel.npy               输入样本（128×128 int64）
    └── sentinel/                         生成的完整 C 工程
        ├── weights.h  (10.2 KB)          ← 8bit 权重
        ├── cnn.c / cnn.h
        ├── main.c / softmax.c
        ├── Makefile / project.mk
        └── .vscode/                      调试配置
```

## 模型结构

```
输入 折叠PCM (128, 128)
  ↓ [频率强调层 x⊙σ(w·s)]      ← 已折叠进 conv1 权重，上板时不存在
  ↓ Conv1d(128→8,  k=1, p=0) + ReLU              → (8, 128)
  ↓ MaxPool(2) + Conv1d(8→12, k=3, p=1) + ReLU   → (12, 64)
  ↓ MaxPool(4) + Conv1d(12→16, k=3, p=1) + ReLU  → (16, 16)
  ↓ AvgPool(16) 全局平均池化                       → (16, 1)
  ↓ 摊平 → 16 维 embedding
  ↓ Linear(16 → 2)                                 → 正常/异常 logits
```

## 三个关键设计（抄自 DrongoNet，arXiv 2607.19721）

1. **极窄通道**：最宽只有 16 通道（对比现役哨兵的 100+）
2. **GAP 全局平均池化替代 FC 层**：砍掉参数大户，embedding 直接用于质心法
3. **频率强调层替代 BatchNorm**：`x ⊙ σ(w·s)`，仅 129 参数，**量化安全**（BN 在 INT8 下会退化）
   - 该层线性，**可数学折叠进 conv1**：`conv1(x⊙g) = (W⊙g)(x)`
   - 上板时不存在，故 ai8x 版参数 2,003 < PyTorch 版 2,087

另外用了 **focal loss**（γ=2.0）处理类别不平衡。

## 完整流水线

```powershell
# 环境：ai-train（训练）/ ai8x（量化上板）

# 1. 训练 + 评测（ESC-50 突发声 vs 平稳背景）
python code/tiny_sentinel.py --width 8,12,16 --k1 1 --epochs 60 --tag b2087

# 2. 迁移到 ai8x（含 FreqEmphasis 折叠）
python code/export_ai8x.py

# 3. 量化（在 ai8x-synthesis 目录）
python quantize.py weights/sentinel_tiny_ai8x.pth.tar weights/sentinel_tiny_ai8x_q8.pth.tar `
  --device MAX78000 -c max78000/sentinel_tiny-hwc.yaml

# 4. 生成 C 代码（在 ai8x-synthesis 目录）
python ai8xize.py --no-version-check --overwrite --test-dir <out> --prefix sentinel `
  --checkpoint-file weights/sentinel_tiny_ai8x_q8.pth.tar `
  --config-file max78000/sentinel_tiny-hwc.yaml --device MAX78000 `
  --sample-input max78000/sample_sentinel.npy
```

## 参数扫描结果（找最小可用规模）

| 结构 | k1 | 参数量 | baseline 区分度 |
|---|---|---|---|
| (8,12,16) | 3 | 4,135 | 5.45 |
| **(8,12,16)** | **1** | **2,087** ⭐ | **5.07~5.19** |
| (6,8,12) | 3 | 2,917 | 2.86 |
| (4,6,8) | 1 | 893 | 3.20 |
| （现役 7 万参数哨兵） | — | 69,556 | 5.74 |

**重要发现**：`k1`（首层卷积核）比通道数更关键——`k1=3` 时首层吃掉 79% 参数，后面层没容量，效果反而差。

## 数据来源

- **ESC-50**（正常 16 类稳态背景 / 异常 8 类突发声）
  - 正常：rain, wind, sea_waves, crickets, vacuum_cleaner, washing_machine, engine, train, airplane, helicopter, clock_tick, snoring, breathing, crackling_fire, insects, chainsaw
  - 异常：glass_breaking, door_wood_knock, clapping, fireworks, siren, car_horn, clock_alarm, thunderstorm
- **评测**：`max78000/baseline_16k.wav`（寝室录音，正常=鼠标/风扇，异常=放手机 4.1s、5.1s）

## MAX78000 关键约束

1. 池化窗口 ≤ 16（本结构用 pool 2/4/16，最后 GAP 用 pool(16)）
2. `processors` = 输入通道侧，`output_processors` = 输出通道侧（都要显式写）
3. 输入 128 通道 → processors 需 **64 位**掩码
4. 不支持的：depthwise 卷积、BatchNorm（故用频率强调层替代）
5. ai8xize 需 `--no-version-check`
6. sample 必须是 **int64** 的 (128,128) 数组
