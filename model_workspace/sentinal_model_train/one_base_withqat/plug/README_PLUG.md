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

现役链路是「HPF → `sample*4/256` → 转置」，**没有归一化**。本模型训练时是逐带归一化的，
所以要在 `vTaskAudioCapture_process` 里、每个 chunk（128 点）攒满、进 `AddTranspose` 之前插：

```c
/* pChunkBuff[0..127] = 当前这一带（一行）的 128 个 int8 样本 */
if (chunkCount == CHUNK) {
    chunkCount = 0;

    /* --- 逐带归一化 + 重量化，必须加 --- */
    int32_t sum = 0;
    for (int i = 0; i < CHUNK; i++) sum += (int8_t)pChunkBuff[i];
    float mean = (float)sum / CHUNK;
    float var = 0.0f;
    for (int i = 0; i < CHUNK; i++) {
        float d = (float)(int8_t)pChunkBuff[i] - mean;
        var += d * d;
    }
    float std = sqrtf(var / CHUNK);
    for (int i = 0; i < CHUNK; i++) {
        float xn = ((float)(int8_t)pChunkBuff[i] - mean) / (std + 1e-5f);
        int32_t q = (int32_t)roundf(xn * 16.0f);   /* ×16 来自 QAT conv1.output_shift=-4 */
        if (q > 127) q = 127;
        if (q < -128) q = -128;
        pChunkBuff[i] = (uint8_t)(int8_t)q;
    }
    /* ----------------------------------- */

    ret = AddTranspose(pChunkBuff, cur_pAI85Buffer, CHUNK, SAMPLE_SIZE, TRANSPOSE_WIDTH);
    ...
}
```

需要 `#include <math.h>`（`sqrtf`/`roundf`）。

## 四、两个可调项

1. **`SAMPLE_SCALE_FACTOR`（`tasks_manage.h`）**：现在是 4 → `sample*4/256 = s/64`，
   `|s|>8192` 会 uint8 饱和。归一化会抹掉整体尺度，但**饱和的信息救不回来**。
   建议接 sen1 时先改回 `1`（`s/256`，不饱和）。
2. **归一化里的 `16.0f`**：来自 QAT `conv1.activation_threshold=4` / `output_shift=-4`
   （`2^(8-1)/2^(4-1) = 16`）。如果上板后真实人声识别不对，优先微调这个乘数（8~32）。

## 五、上板自检顺序

1. 先别接麦克风：把 `main.c` 换成自带的 `sampledata.h` 走一遍 `check_output()`，确认 KAT PASS。
2. 再接麦克风：说话时 `margin` 应明显 > 0，安静时 < 0。
3. 不对就按 §四 调 ×16 和 SAMPLE_SCALE_FACTOR。
