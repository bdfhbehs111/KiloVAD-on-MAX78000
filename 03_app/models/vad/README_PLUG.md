# vad_cnn 无缝接入包（two_base 实验）

三个文件，已经在 `03_app/models/vad/`，`project.mk` 的 `VPATH / IPATH` 已挂好：

| 文件 | 说明 |
|---|---|
| `vad_cnn.c` | CNN 驱动 + 模型配置 + FreeRTOS ISR（已接好 `cnn_isr` 任务通知） |
| `vad_cnn.h` | API，全部 `vad_cnn_*` 前缀；定点类型/softmax 走 `model_common.h` |
| `vad_cnn_weights.h` | 量化权重（**10,784 B / 2.4%**） |

模型来源：`one_base_distill/ckpts/t7_kd_s1001.pth.tar`
（剪枝 32/24/32/16/8/16 → 5ep CE 微调 → 8ep 自蒸馏 → ShiftQAT 10ep → `quantize.py --clip-method SCALE`）

## 一、与现役 `sen1_cnn` 的差异（三条，必须知道）

| | sen1_cnn | **vad_cnn** |
|---|---|---|
| 通道 | 64/96/96/64/32/16 | **32/24/32/16/8/16** |
| 权重 | 79,392 B (17.9%) | **10,784 B (2.4%)** |
| 硬件 ops | 3,838,512 | **814,512（−78.8%）** |
| bias | 370 B | **130 B** |
| 输出地址 | 0x50404000 | **0x50404000（相同）** |
| 输出解码格式 | raw int8，`val&0xff` / `(val>>8)&0xff` | **完全相同** |
| ISR 函数名 | `CNN_ISR` | **`VAD_CNN_ISR`** |

**① ISR 改名了。** `sen1_cnn.c` 已经定义了 `void CNN_ISR(void)`，两个模型文件同时参与编译时
同名非 static 函数会在链接期撞符号。所以 vad 的 ISR 叫 `VAD_CNN_ISR`，它自己
`MXC_NVIC_SetVector(CNN_IRQn, VAD_CNN_ISR)` —— 对 app 完全透明，你不用碰。

**② 输出地址与解码格式和 sen1 一模一样**，所以 `tasks_manage.c` 里现役这两行原样可用：

```c
int8_t s0 = (int8_t)(sen_out2 & 0xff);          // 类0 = 非人声
int8_t s1 = (int8_t)((sen_out2 >> 16) & 0xff);  // 类1 = 人声
int margin = (int)s0 - (int)s1;                 // margin < 0 才是人声
```

（`vad_cnn_unload` 内部写的是两个连续 `uint16`：`out_buf[0]=val&0xff`、`out_buf[1]=(val>>8)&0xff`，
小端下 `uint32 = [b0 00 b1 00]`，所以 app 侧 `&0xff` 取 b0、`>>16` 取 b1。）

**③ 未调用时整个模块被链接器 GC 掉。** 工程开着 `-ffunction-sections -fdata-sections` +
`--gc-sections`，只要 `tasks_manage.c` 还没调 `vad_cnn_*`，`vad_cnn.o` 虽然编译了但不会进
最终镜像 —— 实测加进 VPATH 后 FLASH 仍是 135 KB（26.37%），一字节没涨。
真正换过来之后，符号大小对比：`sen1_cnn.o` 的 `kernels` 是 82,436 B，`vad_cnn.o` 是 **12,996 B**。

## 二、要改的就是 `tasks_manage.c`（这是应用层，我一个字没动）

1. `#include "sen1_cnn.h"` → `"vad_cnn.h"`
2. `sen1_cnn_*` 全部 → `vad_cnn_*`（`_enable / _init / _load_weights / _load_bias / _configure /
   _start / _unload / _disable`，还有 `sen1_cnn_time` → `vad_cnn_time`）
3. 逐带归一化那段**不用改**，乘数仍是 `×16.0f`（已重新标定，见 §四）

## 三、上板自检：先跑 KAT，别接麦克风

本次 ai8xize 用 `_gin/voice0_k16.npy`（人声）作 `--sample-input`，生成的
`sampleoutput.h` 是：

```
{ 0x50404000, 0x0000ffff, 0x00000001, 0x000006f7, 0x00000000 }
```

地址 `0x50404000` 的低 16 位应为 **`0x06f7`** → 拆成 `s0 = 0xf7 = −9`、`s1 = 0x06 = +6`，
**`margin` 必须等于 −15**。不等于 −15 就说明加速器/权重搬运/输出解码有问题，和麦克风无关。

（sen1 的 KAT 是 −18，vad 是 −15，别拿旧数对。）

## 四、增益 k 重标定结果：仍然是 16

剪枝后重扫了 `k ∈ {4,8,16,32,64}`（`probe.py --grid`，ai8xize 整型仿真，每点 ~2.7 s）：

| k | voice0 | voice1 | noise0 | noise1 |
|---|---|---|---|---|
| 4 | — | **+3（错）** | +6 | +5 |
| 8 | — | −3 | +5 | +5 |
| **16** | **−15** | **−16** | **+5** | **+10** |
| 32 | −17 | −21 | **−3（错）** | +10 |
| 64 | −9 | −17 | **−3（错）** | +12 |

`k=16` 仍是拐点：人声全部为负且聚得紧，噪声多数为正；再往上噪声开始往负走。
**所以 app 侧 `roundf(xn * 16.0f)` 和 `SAMPLE_SCALE_FACTOR = 1` 都不用改。**

## 五、12 样本判别力验收（量化后，ai8xize 整型仿真）

```
EXT_zero    +7      EXT_pos127  +11     EXT_neg128  +12     EXT_alt     +11
voice0_k16  -15     voice1_k16  -16     voice2_k16  -13     voice3_k16  -10
noise0_k16  +5      noise1_k16  +10     noise2_k16  -2      noise3_k16  +10
```

- 判据 1（全零 vs 真实人声必须不同）：**通过**，+7 vs −15…−10
- 判据 2（同类不同样本不能全一样）：**通过**，−15/−16/−13/−10
- 判据 3（方向）：人声 4/4 为负；非人声 3/4 为正（noise2 = −2，一个误报）

对照 sen1（k=16）：人声 −18/−23/−24/−9、噪声 +7/+13/−11/+14（也是 3/4）。
**同等判别力，cycle 少 67.9%。**

## 六、量化阶段的两个坑（已在流程里处理，换模型时注意）

1. **`quantize.py` 必须带 `--clip-method SCALE`**。裸跑会沿用 QAT 的 per-layer shift
   （按权重幅度推导、不看激活分布）→ 整型前向退化成偏置常数，全零输入和真实人声输出一样，
   板上恒报人声。
2. **yaml 的 `processors` 不能只写一个掩码**。剪枝后 `out < 64`，输入侧和输出侧的处理器数
   不再相等，必须同时写 `processors`（= `ceil(in/64)` 趟的每趟处理器数）和
   `output_processors`（= `ceil(out/64)` 趟的每趟处理器数）。只写一个会报
   `has N bits instead of the expected number of M`。
3. **`vad_cnn_unload` 里的左移量不是固定值**：sen1 生成的是 `<< 5`，vad 生成的是 `<< 4`。
   必须用正则去掉任意位数，写死 `<< 5` 的字符串替换会静默失效，留下 `<< 4` 后
   `(0xf7 << 4) & 0xff = 0x70`，margin 从 −15 变成 +112。
