# sen1_cnn — MAX78000 上板测试模型（E2.5）

本目录由 `ai8xize.py` 自动生成的 C 代码，对应 **one_base 基线 + 逐带归一化** 经 **ShiftQAT** 量化后的模型。

## 1. 生成链路（可复现）

```
float 基线 one_base (ep27)                    → one_base_best.pth.tar
  └─ ShiftQAT 继续训练 (ep30 切入 QAT，ep42 最优) → one_base_qat_best.pth.tar   (val Top1 97.225)
       └─ quantize.py（QAT-aware，无 --clip-method）→ one_base_qat_best-q.pth.tar  (int8 权重)
            └─ ai8xize.py --device MAX78000     → 本目录
```

- QAT checkpoint: `sentinal_model_train/ai8x-training/logs/one_base___2026.11.04-104409/one_base_qat_best.pth.tar`
- int8 checkpoint: 同目录 `one_base_qat_best-q.pth.tar`
- 配置: `model_workspace/sen1_cnn.yaml`

## 2. 资源占用（编译器报告）

| 项 | 数值 |
|---|---|
| 运算量 | 3,838,512 ops（3.80M macc） |
| 权重内存 | 79,392 B / 442,368 B = **17.9%** |
| Bias 内存 | 370 B / 2,048 B = 18.1% |

## 3. 文件说明

| 文件 | 作用 |
|---|---|
| `cnn.c` / `cnn.h` | CNN 驱动 + 对外 API（`cnn_enable/init/load_weights/load_bias/configure/start/unload` 等） |
| `weights.h` | 量化后的 int8 权重 |
| `sampledata.h` | 自带样例输入（KAT 用） |
| `sampleoutput.h` | 该样例的期望输出（KAT 用） |
| `main.c` | 测试主程序：加载输入→跑一次推理→`check_output()` 比对→打印 PASS/FAIL |
| `Makefile` / `project.mk` | MSDK 构建（`project.mk` 留空待你填） |

## 4. 硬件输入格式（关键）

`main.c` 的 `load_input()` 已给出唯一需要你复刻的物理格式：

- 输入 = **128 通道 × 128 时间点 = 16384 个 int8**。
- 在内存里不是平铺，而是 **16 块 × 256 个 32 位字**，每字压 4 个通道（HWC 128x1），起点 `0x50400000` 起。
- `load_input()` 里 16 次 `memcpy32` 就是这 16 块的地址。**整段格式与模型无关，由 MAX78000 的 HWC 数据格式决定**——你自己的固件必须按这个格式喂数。

## 5. 上板预处理契约（你必须在固件里实现）

训练时数据是「逐带归一化」的，硬件只收 int8。所以要复刻训练输入，固件需按顺序做：

1. 原始音频 →（fold）成 128 块 × 128 点，int8 量化：`q = clip(round(x*128), -128, 127)`。
2. **逐带归一化**（对每个通道跨 128 个时间点）：
   `x_norm = (q - mean) / (std + eps)`，eps=1e-5。
3. 归一化结果（float，约 `[-8, 8]`）**重量化到 int8**：
   `x_int8 = clip(round(x_norm * 16), -128, 127)`。
   （尺度 16 来自 QAT 记录的 `conv1.activation_threshold=4`、`conv1.output_shift=-4`；
   即 `2^(8-1) / 2^(4-1) = 2^(-output_shift) = 16`。见 §7 校准提示。）
4. 按 §4 的 16 块 × 256 字格式写入 `0x50400000` 起的输入区。
5. 启动 CNN，读回 1 个输出字（地址 `0x50404000`，`sampleoutput.h` 里可查），即 2 类的分数。

## 6. 期望输出

2 类（voice / non-voice），硬件输出 1 个 32 位字（`sampleoutput.h` 中 `0x50404000`）。
`check_output()` 会把读回值与期望比对；样例输入下应打印 `*** PASS ***`。

## 7. 校准提示（上板第一步）

- 先跑 `main.c` 自带的样例（`sampledata.h`），确认硬件与仿真一致（KAT PASS）。
- 再用你的真实音频；如果 KAT 过但真实音频识别不对，**优先怀疑 §5 第 3 步的尺度 16**：
  它是从 QAT 内部 `output_shift` 反推的，最稳的验证方法是在板上用一段已知"有/无人声"音频，
  微调这个乘数（16 附近），看输出分数分布能否把两类分开。
- 归一化本身（第 2 步）是确定的，不要动。
