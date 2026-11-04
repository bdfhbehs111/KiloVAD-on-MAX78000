# sen1_cnn 无缝接入包

三个文件，直接丢进 `04_app/models/sen1/`：

| 文件 | 说明 |
|---|---|
| `sen1_cnn.c` | CNN 驱动 + 模型配置 + FreeRTOS ISR（已按 `sen_cnn.c` 的模式接好 `cnn_isr` 通知） |
| `sen1_cnn.h` | API，全部 `sen1_cnn_*` 前缀；定点类型/softmax 走 `model_common.h` |
| `sen1_cnn_weights.h` | 量化权重（79,392 B / 17.9%） |

## 一、和现役 `sen_cnn` 的 API 对应（`sen_cnn_*` → `sen1_cnn_*`）

`sen_cnn_enable` / `sen_cnn_boost_enable` / `sen_cnn_init` / `sen_cnn_load_weights` /
`sen_cnn_load_bias` / `sen_cnn_configure` / `sen_cnn_start` / `sen_cnn_unload` / `sen_cnn_disable`
→ 全部把前缀 `sen_cnn_` 换成 `sen1_cnn_` 即可。

`CNN_ISR` 保持不变（和其它模型共用同一个 ISR 入口，内部已改成通知 `cnn_isr` 任务）。

## 二、构建（`04_app/project.mk` 加两行）

```make
VPATH += models/sen1
IPATH += models/sen1
```

> 注意：如果同时保留 `sen_cnn.c` 和 `sen1_cnn.c`，两个文件都定义了 `CNN_ISR` → 链接冲突。
> 二选一：删掉旧 `sen_cnn.c`，或把 `sen1_cnn.c` 里的 `CNN_ISR` 删掉（共用旧的）。

## 三、`tasks_manage.c` 要改的 3 处

### 1) 调用改名
`vTaskCNN` 里的 `sen_cnn_*` 全部 → `sen1_cnn_*`。

### 2) 输出解码：不用改
`sen1_cnn_unload` 已被我改成和现役 `sen_cnn` **完全同格式**（raw int8，`val&0xff` / `(val>>8)&0xff`，
无 `<<5`）。所以 `tasks_manage.c` 里现有这两行原样可用：

```c
int8_t s0 = (int8_t)(sen_out2 & 0xff);
int8_t s1 = (int8_t)((sen_out2 >> 16) & 0xff);
int margin = (int)s0 - (int)s1;
```

> 唯一区别：本模型输出地址是 `0x50404000`（现役是 `0x50402000`），这个已经封在
> `sen1_cnn_unload()` 里，你不需要碰。

### 3) 预处理：逐带归一化（核心，必须加）

训练侧 `datasets/sentinel.py::normalize_per_band` 是**沿 dim1（时间块轴）**求 mean/std 的，
样本形状 `(128,128) = (dim0=块内采样位置/通道, dim1=时间块)`，增强 `np.roll(axis=1)` 也印证轴 1 是时间。

所以「一条带」= **固定 dim0、跨 128 个时间块**取 128 个点；**不是**固定某一时刻的 128 个通道。

但 `pChunkBuff[128]` 恰恰只是**某一个时间块的全部 128 个块内位置**（dim1=k 的一列）。
拿它对 mean/std 就是在沿 dim0 归一化 —— **轴向反了，等于没做**。
必须等 128 个 chunk 攒满、`AddTranspose` 把 128×128 摆进 `cur_pAI85Buffer` 之后，再在这块缓冲上按列做。

落位公式（`AddTranspose` 里 `wordRow = secondHalf + (row<<1)`）：
`index = 1024*((col%64)/4) + 4*(col>=64 ? 1 : 0) + 4*2*row + (col%4)`。
固定 `col` 时 `row=0..127` 正好是 **`base + 8*row`** 的等差。

```c
if (ret) {                          /* ret = AddTranspose(...) 的返回值 */
    for (int col = 0; col < 128; col++) {
        int base = 1024 * ((col % 64) / 4) + 4 * (col >= 64) + (col % 4);
        int32_t sum = 0;
        for (int r = 0; r < 128; r++) sum += (int8_t)cur_pAI85Buffer[base + 8*r];
        float mean = (float)sum / 128.0f;
        float var = 0.0f;
        for (int r = 0; r < 128; r++) {
            float d = (float)(int8_t)cur_pAI85Buffer[base + 8*r] - mean;
            var += d * d;
        }
        float std = sqrtf(var / 128.0f);
        for (int r = 0; r < 128; r++) {
            float xn = ((float)(int8_t)cur_pAI85Buffer[base + 8*r] - mean) / (std + 1e-5f);
            int32_t q = (int32_t)roundf(xn * 16.0f);   /* ×16，见 §四.2 */
            if (q > 127)  q = 127;
            if (q < -128) q = -128;
            cur_pAI85Buffer[base + 8*r] = (uint8_t)(int8_t)q;
        }
    }
    /* 归一化完再入队 */
}
```

> ⚠ **不要 `#include <math.h>`**。newlib 的 `math.h` 顺带声明了 Bessel 函数 `y0()` / `y1()`，
> 和 `tasks_manage.c` 里 HPF 的状态变量 `y0` / `y1` 重名，直接
> `error: 'y0' redeclared as different kind of symbol`。
> 改用两条本地声明即可（`libm` 由 `gcc.mk:517` 的 `STD_LIBS=-lc -lm` 链进来）：
>
> ```c
> extern float sqrtf(float x);
> extern float roundf(float x);
> ```

## 四、四个可调项

1. **`SAMPLE_SCALE_FACTOR`（`tasks_manage.h`）**：现在是 `4` → `sample*4/256 = s/64`。
   注意 `(uint8_t)` 是**回绕不是饱和**：`|s| > 8191`（25% 满量程）就整段翻符号，
   归一化算出来的 mean/std 直接作废。**建议改成 `1`**（`s/256` → ±127，正好用满 int8）。
   归一化本身尺度不变，所以改这个不影响归一化的正确性，只影响有没有回绕。
2. **乘数是 `16`（实测标定，不是推的）**。用 ai8xize 的整型仿真扫 `k ∈ {1,2,4,...,128}`：

   | k | 人声 s0−s1 | 非人声 s0−s1 |
   |---|---|---|
   | 1~4 | +12 / +11 / +9（全部误判成非人声） | +12 / +9 / +11 |
   | 8 | +3 / −4 / −4 / +3 | +9 / +9 / +4 / +14 |
   | **16** | **−18 / −23 / −24 / −9（4/4 全对）** | +7 / +13 / −11 / +14 |
   | 32 | −26 / −43 / −36 / −23 | −1 / +16 / −10 / +15 |
   | 64 | −10 / −36 / −32 / −23 | −3 / +27 / −3 / +15 |

   `k=16` 是拐点：人声全部为负且聚得紧，噪声多数为正。再往上噪声开始往负走，不建议。
3. **`margin` 的符号是反的**：`output: ('nonvoice', 'voice')` → `s0`=类 0=非人声、`s1`=类 1=人声，
   所以 **`margin = s0 - s1 < 0` 才是人声**。浮点模型上 4 个人声是 −19.5/−27.3/−11.7/−15.8，
   4 个非人声是 +3.4/+8.2/−2.1/+5.5 —— 和 int8 的符号逐个对得上。
4. **归一化别放在音频任务里**。128 列 × 3 遍 × 128 点 ≈ 4.9 万次浮点迭代 + 128 次 `sqrtf`，
   在 60 MHz 上估计 20~50 ms。这期间 `vTaskAudioCapture_process` 不回来 `ulTaskNotifyTake`，
   I2S FIFO 没人掏，下一帧前段采样会丢。
   建议把这段挪到 `vTaskCNN` 里、`cnn_load_data(p_infer)` **之前**——那本来就是「准备加速器输入」的位置，
   而且 `p_infer` 指向的缓冲区生产者已经在写另一块，不会被踩。

> ⚠ 本模型**必须**用 `quantize.py --clip-method SCALE` 量化。不带 `--clip-method`（沿用 QAT 的
> per-layer shift）会让整型网络被偏置支配：全零输入和真实人声输出完全一样，板上会恒报人声。
> 另外 `izer/quantize.py` 有个上游 bug（`distribution_factor` 在非 `get_max_bit_shift` 分支未初始化，
> 给 `--clip-method` 就 `UnboundLocalError`），本项目已补一行默认值。

## 五、上板自检顺序（先别接麦克风）

`sen1_cnn` 自带**已知答案测试**，完全不依赖麦克风，是上板第一步：
`sampleoutput.h` 里 `SAMPLE_OUTPUT = { 0x50404000, 0x0000ffff, 1, 0x000002f0 }`，
即地址 `0x50404000` 低 16 位应为 `0x02f0` → 拆成 `s0 = 0xf0 = −16`、`s1 = 0x02 = +2`，
**`margin` 必须等于 −18**（顺带：这个 KAT 用的输入样本是人声，−18 也正好是「人声」）。

1. 把 `sampledata.h` 拷进来，临时让 `vTaskCNN` 不用队列、直接按
   `SAMPLE_INPUT_0 / _4 / _8 … _60` 灌 `0x50400000…` 那 16 个 1 KB 块（顺序见 `load_input()`），
   **跳过归一化**，跑一次看 `margin == −18`。不等于 −18 就说明加速器/权重搬运/输出解码有问题，
   跟麦克风和归一化都无关，别往下走。
2. KAT 通过后再接麦克风：说话时 `margin` 应明显 **< 0**，安静/环境噪声时 > 0。
3. 还不对，才在 §四.2 的表里换 k（10~24 之间细扫）。

