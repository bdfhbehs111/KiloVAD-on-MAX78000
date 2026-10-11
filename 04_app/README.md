# 04_app — sys_agent 的 FreeRTOS 多任务应用（可编译骨架）

> **这是下一步「RTOS 多任务调度」的起点工程。**
> 两个模型已经合并、改名、验证过共存；9 个任务的骨架和同步关系都搭好了；
> `main.c` 只留 include + `main()` 本体，任务细节留给你填。

---

## 一、当前状态（实测）

| 项目 | 状态 |
|---|---|
| 编译 | ✅ 通过，**零警告零错误** |
| Flash | **90,624 B / 512 KB = 17.29%**（两个模型权重都在里面） |
| SRAM | **63,068 B / 130,944 B = 48.16%** |
| 两个模型共存 | ✅ 已验证：`sen_cnn_*` 与 `kws_cnn_*` 同时存在于最终固件，无符号冲突 |
| 任务逻辑 | ⬜ 空壳：同步对象已建好，任务各自阻塞等事件，往里填 TODO 即可 |
| 上板实测 | ⬜ 未做 |

---

## 二、目录结构

```
04_app/
├── main.c                 ⭐ 只有 include + main() 本体（上电→初始化→交棒调度器）
├── app_tasks.c            ⭐ 9 个任务 + 同步对象 + 帧缓冲池（你要填的主体）
├── app_tasks.h            对外接口、共享数据结构、模型接口表
├── app_config.h           ⭐ 所有可调参数（引脚/缓冲/优先级/栈/阈值）
├── FreeRTOSConfig.h       本项目定制的内核配置
├── project.mk             工程配置（LIB_FREERTOS=1、VPATH/IPATH）
├── Makefile               MSDK 通用 Makefile（不要改）
├── models/                两个模型合并后的产物
│   ├── model_common.h     共享的定点类型 + softmax 原型
│   ├── softmax.c          两模型共用一份
│   ├── sen/               sen_cnn.c / sen_cnn.h / sen_weights.h
│   └── kws/               kws_cnn.c / kws_cnn.h / kws_weights.h
└── tools/
    └── namespace_models.py   模型改名脚本（可重跑，幂等）
```

---

## 三、编译

### 方式 A：用顶层 CMake（推荐）

```powershell
cd <sys_agent_max78000>
cmake -S . -B build -G Ninja         # 默认 MAXIM_PATH=D:/MaximSDK
cmake --build build --target app     # 编译本工程
cmake --build build --target app-size
cmake --build build --target list-targets   # 看全部目标
```

### 方式 B：直接用 MSDK 的 Makefile

```powershell
D:\MaximSDK\setenv.bat               # 设 MAXIM_PATH 和 PATH
cd <sys_agent_max78000>\04_app
make -r -j 8 TARGET=MAX78000 BOARD=FTHR_RevA MAXIM_PATH=D:/MaximSDK
```

> **板子**：默认 `FTHR_RevA`（MAX78000FTHR，**板载麦克风**，音频采集必须用它）。
> 用 `EvKit_V1` 也能编，但没有板载麦克风，I2S 部分跑不起来。
>
> ⚠ **别同时编多个工程**。MSDK 把外设驱动编成全工程共享的
> `Libraries/PeriphDrivers/bin/<芯片>/*.a`，并行编多个工程会在建这个库时互相踩，
> 表现为随机的 `Error 1` 且看不到任何编译错误。

---

## 四、两个模型是怎么合并的（**关键**）

### 问题

哨兵和中文口令都由 ai8xize 生成，`cnn.c` / `cnn.h` 里的符号**完全同名**：

```
cnn_enable / cnn_init / cnn_configure / cnn_load_weights / ... / cnn_time
CNN_ISR / CNN_OK / CNN_FAIL / CNN_NUM_OUTPUTS    ← 一个是 1，一个是 26！
memcpy32
```

直接把两份丢进一个工程 = 重复定义 + 宏冲突，必定链接失败。

### 解决

`tools/namespace_models.py` 一次性做掉（可重跑）：

| 动作 | 结果 |
|---|---|
| 加命名空间前缀 | 哨兵 → `sen_*`；中文口令 → `kws_*` |
| 文件改名 | `cnn.c/h` → `sen_cnn.c/h`、`kws_cnn.c/h`；`weights.h` → `sen_weights.h`/`kws_weights.h` |
| 修 `#include` | 跟着改名，避免找不到头文件 |
| 抽出公共部分 | `q31_t`/`q15_t` 和 softmax 原型 → `model_common.h`（两模型完全相同，只留一份） |
| 共用实现 | `softmax.c` 两模型逐字节相同，只编译一份 |
| 保留 CMSIS 符号 | `CNN_IRQn` / `CNN_FIFO_IRQn` 是芯片定义，**不能改**（脚本自动识别白名单） |
| 保留编译开关 | `CNN_INFERENCE_TIMER` 保持原名，一个宏同时打开两个模型的计时 |

### 怎么复核

```powershell
# 1. 重跑脚本，自检会报告有无残留裸符号
python tools/namespace_models.py

# 2. 编完之后确认两个模型都在固件里
arm-none-eabi-nm --defined-only build/max78000.elf | findstr "sen_cnn_ kws_cnn_"
```

### 模型统一接口表

`app_tasks.c` 里的 `g_model_sen` / `g_model_kws` 把两套同形状的 API 统一成
`app_model_t`，上层不用写 if-else。这张表也是**共存性的编译期证明**——
它引用了两边的符号，链接器就不能把任何一个模型当死代码回收。

---

## 五、📊 SRAM 账（**动手前先算**）

MAX78000 只有 **128 KB SRAM**（130,944 B），Flash 512 KB。
CNN 加速器有**独立的 442 KB 权重内存，不占 SRAM**。

| 用途 | 大小 | 说明 |
|---|---|---|
| 帧缓冲池 `APP_FRAME_POOL` × 16 KB | **32 KB** | 已实现，在 `app_tasks.c` |
| I2S DMA 小 ring `APP_I2S_DMA_SAMPLES` × **4 B** | **4 KB** | ⚠ 32-bit/样本；**尚未声明**，填任务 1 时要加 |
| FreeRTOS 堆 | **24 KB** | 9 个任务栈 + 队列都从这里出 |
| .data/.bss 其他（模型权重索引等） | ≈ 5 KB | 实测 |
| **合计** | **≈ 65 KB / 128 KB** | |

> ⚠⚠ **别让 DMA 一次收满一帧。** 样本是 **32 位**，16384 点 = **64 KB**，
> 再加帧池 32 KB 就把 128 KB 的 SRAM 吃干了。
> 正确做法：小 ring（4 KB）+ 半满/全满中断，在任务里**边收边折叠散写**到帧缓冲
> （折叠下标映射是确定的：样本 `i` → `data[(i%128)*128 + i/128]`）。
> 见 `app_tasks.c` 的 TODO(3)。
>
> 还有余量时可以考虑：
> 1. 把折叠结果**直接写进 CNN 输入内存**（`0x50400000` 起，加速器自己的内存，
>    不占 SRAM）—— 连 32 KB 帧池都能省掉
> 2. 砍 `APP_FRAME_POOL`（改成 1，前后级严格串行）
> 3. 减小 `APP_FRAME_HOP` 反而更费 CPU，不影响内存

改成静态分配（`configSUPPORT_STATIC_ALLOCATION`）还能把 24 KB 堆让出来一部分。

---

## 五之二、⚠ I2S 位宽：**32 位字 / 18 位有效数据**

这一条曾经被我写错（写成 16 位），教训记在这里。

**实测结论**（证据链）：

| 环节 | 事实 | 出处 |
|---|---|---|
| I2S 总线字宽 | **32 位** | `I2S_DMA/main.c`、`kws20_demo/main.c` 都是 `bitsWord = 32; sampleSize = MXC_I2S_SAMPLESIZE_THIRTYTWO;` |
| 麦克风有效数据 | **32 位字的"高 18 位"** | `kws20_demo/main.c` 原注释：`/* The actual value is 18 MSB of 32-bit word */` |
| 取出 16 位样本 | `int16_t s = (int16_t)((int32_t)word >> 14);` | 同上，下一行 |
| 再降到 8 位喂 CNN | `micBuff[i] = sample * SAMPLE_SCALE_FACTOR / 256;`（factor = 4） | 同文件 L1229 |

**哪块板子用哪种麦克风**：

| 板子 | 麦克风通路 | 上电方式 |
|---|---|---|
| `FTHR_RevA` | **数字 MEMS 麦**（直连 I2S），由 PMIC MAX20303 供电 | `Microphone_Power(POWER_ON)` |
| `EvKit_V1` | **MAX9867 音频 codec** | `codec_init()`（`Microphone_Power()` 直接返回 `E_NOT_SUPPORTED`） |

**对代码的三点影响**（已反映到 `app_config.h`）：

1. `req.bitsWord = 32; req.sampleSize = MXC_I2S_SAMPLESIZE_THIRTYTWO;`
2. **DMA 缓冲必须是 `uint32_t[]`**，一帧 16384 点就是 64 KB → 必须用小 ring 分块收
3. 折叠 + 量化可以化简成**一次右移**：

   ```
   训练侧  q = clip(round((s/32768 + 1) * 128), 0, 255) - 128
   板上    word(32bit) ──(>>14)──▶ int16 s ──(>>8)──▶ int8 q
           ⇒  q = (int8_t)((int32_t)word >> 22)      // 无需浮点、无需 clamp
   ```

   ⚠ 这个化简依赖"高 18 位"这个前提。**换板子/换麦克风后必须重新确认移位量**，
   否则整帧数据错位（而且不会报错，只会识别率崩掉）。
   对应的宏：`APP_I2S_SHIFT_TO_S16`、`APP_I2S_WORD_TO_INT8()`。

---

## 六、9 个任务与数据流

| # | 任务 | 优先级 | 触发 | 参考实测耗时 |
|---|---|---:|---|---|
| 1 | `vTaskAudioCapture` | 7（最高） | I2S DMA 中断 → `g_sem_audio` | — |
| 2 | `vTaskPreprocess` | 6 | 任务通知 | 纯 CPU 定点 |
| 3 | `vTaskSentinel` | 6 | `g_q_frame` | **≈ 39 µs**（CNN） |
| 4 | `vTaskGate` | 5 | `g_q_gate` | 极短 |
| 5 | `vTaskDeepInfer` | 4 | 任务通知（按需） | **≈ 122 µs**（CNN） |
| 6 | `vTaskReport` | 4 | 深层结果 | softmax 26 类 |
| 7 | `vTaskUartLink` | 3 | `g_q_result` / UART 中断 | — |
| 8 | `vTaskCache` | 2 | 周期 | — |
| 9 | `vTaskMonitor` | 1 | 周期 | 喂狗 + 栈水位 |

```
I2S DMA ISR ──give g_sem_audio──> [1 采集]
   [1] ──g_q_frame──> [2 前处理] ──g_q_frame──> [3 哨兵] ──g_q_gate──> [4 门控]
                                                        ├─ 正常 → 丢弃
                                                        └─ 异常 → notify g_task_deep
   [5 深层] ──写 g_result_log──> [6 结果] ──g_q_result──> [7 串口]
   [7] ──g_q_cmd──> 各任务
   [8] 周期清理 · [9] 喂狗 + 栈水位
```

### 三条不可违反的规则

1. **CNN 加速器必须互斥** —— 单实例硬件，任务 3 和任务 5 用 `g_mtx_cnn` 串行化。
   每次切换模型都要重新 `load_weights()` + `configure()`（两个模型的层配置不同）。
2. **ISR 里只能用 `...FromISR` 版 API**，末尾必须 `portYIELD_FROM_ISR()`。
   而且 ISR 的 NVIC 优先级**数值必须 ≥ `configMAX_SYSCALL_INTERRUPT_PRIORITY`（=5）**，
   否则一调 RTOS API 就 `configASSERT` 挂掉。
3. **两个模型的输出位宽不一样，后处理不能共用**：
   - 哨兵 `output_width: 8` → **8-bit**，2 个类压进 1 个 uint32（拆 `&0xff` / `>>8`）。
     拿到的是原始 logit，**没有额外缩放**（ai8xize 报告 "all output scales are zero"）。
   - 口令 `output_width: 32` → 26 个类各 1 个 uint32（Q17.14），
     这才需要调 `softmax_q17p14_q15()`。

   输入和权重两边**都是 8-bit**（权重按 4 个 int8 打包进 1 个 uint32）。
   完整位宽表见 [`../01_models/README.md`](../01_models/README.md) 第四之二节。

---

## 七、建议的填充顺序

1. **`vTaskAudioCapture`** —— 先把 I2S + DMA 跑通，用 `printf` 确认数据在动。
   参考 `03_api/periph/i2s.md` 和 `MAX78000FreeRTOSDemo`。
   FTHR 板记得先给麦克风上电：`max20303_mic_power(1)`。
2. **`vTaskPreprocess`** —— 折叠 + 量化。**必须和训练时逐位一致**
   （`quantize_audio` + reshape 转置，见 `01_models/*/code/`）。
   把 128×128 的 int8 打几行出来跟 Python 侧对比。
3. **`vTaskSentinel`** —— 接 `g_model_sen`，先跑通完整流程（用 `g_model_sen.init/...`）。
4. **`vTaskGate`** —— 阈值 + 去抖动。阈值要按你的实际环境重算。
5. **`vTaskDeepInfer`** —— 接 `g_model_kws`。
6. **`vTaskReport`** —— `softmax_q17p14_q15()` + 类名表（`01_models/kws26_chinese/weights/kws_classes.json`）。
7. **`vTaskUartLink`** —— 先只发不收。
8. **`vTaskCache` / `vTaskMonitor` / 看门狗** —— 最后加。

### 调试利器

- `uxTaskGetStackHighWaterMark(NULL)` —— 任务栈历史最小剩余量（**字**）。
  任何任务剩余 < 32 字就该加大 `APP_STACK_*`。
- `vTaskGetRunTimeStats()` —— 需要先在 `FreeRTOSConfig.h` 打开
  `configGENERATE_RUN_TIME_STATS` 并配好统计定时器
  （参考 `02_rtos/MAX78000_FreeRTOSDemo/FreeRTOS_Debug.c`）。
- `configCHECK_FOR_STACK_OVERFLOW = 2` 和 `configUSE_MALLOC_FAILED_HOOK = 1`
  **都已打开**，出问题会直接打印是哪个任务 / 堆耗尽，比静默死机好查得多。

---

## 八、已知未完成 / 待决策

| 项 | 说明 |
|---|---|
| **I2S 环形缓冲未声明** | `app_config.h` 里算了 32 KB，但数组还要你在 `vTaskAudioCapture` 里加 |
| **门控阈值是占位值** | `APP_GATE_THRESHOLD 0.50f` 必须用真实环境基线重算 |
| **哨兵用 2 分类头** | 开箱可用。若要 16 维 embedding + 质心距离（更贴合原设计），需改 `models/sen/sen_cnn.c` 的 `sen_cnn_unload()` 去取 layer 3 的 avg_pool 输出（16×int8 = 4×uint32） |
| **贴片** | `APP_USE_TICKLESS_IDLE = 0`。打开前必须先实现 `vPortSuppressTicksAndSleep`（WUT 版），照抄 `02_rtos/MAX78000_FreeRTOSDemo/freertos_tickless.c`，并重写 `freertos_permit_tickless()` |
| **Jetson 协议未定** | UART 帧格式、质心/阈值下发命令，`vTaskUartLink` 的 TODO(11)(12) |
| **烧录** | 见根目录 README 的「烧录」一节 —— 本机 OpenOCD 缺 `max78000.cfg` |

---

## 九、模型实测数据（ai8xize 报告，权威）

| 指标 | 哨兵 `sen` | 中文口令 `kws` |
|---|---|---|
| 参数量 | 2,003 | 29,514 |
| **推理延迟** | **3,894 周期 ≈ 39 µs** @100 MHz | **12,204 周期 ≈ 122 µs** @100 MHz |
| 硬件算子 | 162,848 ops | 1,893,280 ops |
| 权重内存 | 1,920 B / 442,368 B（0.4%） | 29,312 B / 442,368 B（6.6%） |
| 输出 | 2 类，压成 1 个 uint32 | 26 类，26 个 uint32 |
| 独立工程参考 | `01_models/sentinel_gate_bin2/` | `01_models/kws26_chinese/` |

> 💡 两个模型加起来每帧只占 CNN 约 161 µs，而一帧音频是 1.024 s
> （`APP_FRAME_HOP = APP_RING_SAMPLES = 16384 @16 kHz`）。
> **CNN 完全不是瓶颈**，可以放心把滑窗步长调小以降低检测延迟。
