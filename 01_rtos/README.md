# 02_rtos — MAX78000 上跑 FreeRTOS 的实现案例与移植导读

> 目的：为下一步「**RTOS 多任务调度**」打地基——先有一份**能编译、能跑、有实测输出**的官方范例，
> 再照着它把 8 个任务搭起来。

---

## 一、这份案例是什么

**FreeRTOS V10.5.1**（`task.h` 里 `tskKERNEL_VERSION_NUMBER = "V10.5.1"`）
在 **MAX78000 的 ARM Cortex-M4F 核**（100 MHz）上运行的完整工程。

> ⚠ 官方 demo 的 README 打印 `V10.2.0` 是遗留字符串，**实际内核是 V10.5.1**，以 `task.h` 为准。

### 目录

| 路径 | 内容 |
|---|---|
| `MAX78000_FreeRTOSDemo/` | ⭐ **官方范例全量**（可直接 `make` / 烧录） |
| `kernel/` | FreeRTOS V10.5.1 内核（**MSDK 实际编译的那部分** + ARM_CM4F 端口 + 5 种堆 + RISC-V 端口 + FreeRTOS+CLI） |
| `docs/` | 预留：你自己的移植笔记 |
| `../../进展总结.md` | 项目总进度文档 |

### 官方范例里已演示的东西（都是能跑的代码）

| 文件 | 演示内容 | 对本项目的价值 |
|---|---|---|
| `main.c` | 4 个任务、互斥量、任务通知、异步 UART 唤醒任务 | ⭐ **任务+中断+通知的标准骨架** |
| `freertos_tickless.c` | 用 WUT 替代停摆的 SysTick 实现 tickless idle | ⭐⭐ **哨兵低功耗的核心参考** |
| `FreeRTOS_Debug.c` | TMR0 做 RTOS 运行统计定时器；可读的 HardFault 现场保存 | ⭐ 调多任务必用 |
| `CLI-commands.c` | FreeRTOS+CLI 命令行（可选组件） | 调试期方便 |
| `FreeRTOSConfig.h` | 全部内核配置项 | ⭐ 改这里适配本项目 |

---

## 二、怎么在自己的工程里启用 FreeRTOS

**只需在工程的 `project.mk` 里加两行：**

```makefile
LIB_FREERTOS = 1
# 可选：堆方案，默认 4（推荐，抗碎片）
# FREERTOS_HEAP_TYPE := 4
```

然后工程根目录放一份 `FreeRTOSConfig.h` 即可。构建系统（`Libraries\libs.mk` + `FreeRTOS\freertos.mk`）会自动：

1. 把 `FreeRTOS` 编成静态库 `librtos.a`；
2. 加上头文件路径 `Source/include` + `Source/portable/GCC/ARM_CM4F` + 你放 `FreeRTOSConfig.h` 的目录；
3. 链进你的工程。

编译哪些源文件（`FreeRTOS\Makefile` L47-68）：

```
list.c  queue.c  tasks.c  port.c(ARM_CM4F)  timers.c
croutine.c  event_groups.c  stream_buffer.c  heap_<N>.c
```

> ⚠ **MSDK 的 FreeRTOS 构建只支持 ARM Cortex-M4F 核**
> （`VPATH = Source/portable/GCC/ARM_CM4F` 是写死的）。
> 源码树里的 RISC-V 端口只是随内核一起下发的，**没接进构建系统**。
> 本项目的哨兵/深层推理都跑在 M4F 上，RISC-V 暂不参与调度。

### 构建 / 烧录命令（来自 demo 的 `.vscode/tasks.json`）

```bash
# 编译（TARGET=MAX78000, BOARD=EvKit_V1 或 FTHR_RevA）
make -r -j 8 --output-sync=target --no-print-directory \
     TARGET=MAX78000 BOARD=EvKit_V1 MAXIM_PATH=D:/MaximSDK PROJECT=FreeRTOSDemo

# 清理
make -j 8 clean  ...      # 或 distclean 彻底清
```
烧录用 OpenOCD + arm-none-eabi-gdb（见 `.vscode/launch.json`）。

---

## 三、⚠ 硬件资源硬约束（**做任务划分前必读**）

实测自 `03_api/startup_gcc/max78000.ld` 与 `system_max78000.h`：

| 资源 | 容量 | 来源 |
|---|---|---|
| **Flash** | **512 KB** @ `0x10000000` | `max78000.ld` |
| **SRAM** | **≈ 128 KB** @ `0x20000000`（`0x1FF80` = 130,944 B） | `max78000.ld` |
| ROM | 64 KB @ `0x0` | `max78000.ld` |
| 双核共享区 | **仅 128 B**（`SHARED`，`0x2001FF80`） | `max78000.ld` |
| **FreeRTOS 堆** | **26 KB**（`configTOTAL_HEAP_SIZE`） | `FreeRTOSConfig.h` |
| 主频 | 上电 **ISO 60 MHz**；显式选 IPO 后 **100 MHz** | `IPO_FREQ=100000000`、`ISO_FREQ=60000000` |

### 两个必须提前想清楚的账

**① FreeRTOS 堆只有 26 KB，且音频缓冲不能从它出。**
- 8 个任务的栈 + 队列 + 信号量都从这 26 KB 里出。按 1 KB/任务算 ≈ 8 KB，加上队列还行，但**不宽裕**。
- 音频帧按 16384 点 @ 16 kHz 算：`uint16` 缓冲 = 32 KB，**双缓冲就要 64 KB**——直接占掉半个 SRAM，
  而且远超 26 KB 的 RTOS 堆。
- **结论：音频环形缓冲必须用静态全局数组**（放 `.bss`），不能用 `pvPortMalloc`。
  上电时用 `xTaskCreateStatic()` / 静态队列，或干脆全静态分配，把 26 KB 留给真正动态的东西。

**② SRAM 128 KB 要跟 CNN 抢吗？——不抢。**
MAX78000 的 CNN 加速器有**独立的 442 KB 权重内存 + 2 KB 偏置内存**（见下表），不占 SRAM。
所以两个模型的权重不消耗 SRAM，SRAM 只需放：音频缓冲 + 任务栈 + 中间张量。

### 两个模型的实测资源占用（ai8xize 输出，权威）

| 指标 | 极简哨兵（2,003 参数） | 中文口令（29,514 参数） |
|---|---|---|
| **推理延迟** | **3,894 周期 → ≈ 39 µs** @100 MHz | **12,204 周期 → ≈ 122 µs** @100 MHz |
| 硬件算子 | 162,848 ops（158,752 MAC） | 1,893,280 ops（1,878,656 MAC） |
| 权重内存 | 1,920 B / 442,368 B（**0.4%**） | 29,312 B / 442,368 B（**6.6%**） |
| 偏置内存 | 38 B / 2,048 B | 202 B / 2,048 B |

> 💡 **这两个数字决定了任务周期怎么定**：
> 哨兵一次推理只要 39 µs，一帧音频（1.024 s）里 CNN 只忙 0.004% 的时间。
> **CNN 加速器几乎不构成瓶颈**，真正的开销在 I2S 搬数据 + 折叠预处理（纯 CPU 定点）。
> 所以：哨兵可以跑得比一帧更勤（滑窗），深层推理更是随便按需触发。

---

## 四、`FreeRTOSConfig.h` 关键项解读

原文件在 `MAX78000_FreeRTOSDemo/FreeRTOSConfig.h`。逐项说明**哪些能直接抄、哪些必须改**：

| 配置项 | demo 值 | 说明 / 本项目要不要改 |
|---|---|---|
| `configCPU_CLOCK_HZ` | `IPO_FREQ` = **100 MHz** | ✅ 照抄。但注意**上电默认是 ISO 60 MHz**，要 100 MHz 必须自己 `MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO)` + `SystemCoreClockUpdate()` |
| `configTICK_RATE_HZ` | **1000**（1 ms） | ⚠ 16 kHz 采样下 **1 tick = 16 个采样点**。若前处理要按采样点粒度，需提高 tick 或用 DMA 半满中断驱动 |
| `configRTC_TICK_RATE_HZ` | 32768 | ERTCO 32.768 kHz，tickless 用 |
| `configTOTAL_HEAP_SIZE` | **26 KB** | ⚠ 见上，8 任务 + 32 KB 音频缓冲要重新规划 |
| `configMINIMAL_STACK_SIZE` | 128（**字** = 512 B） | 空闲任务栈。普通任务建议 ≥ 1 KB |
| `configMAX_PRIORITIES` | **5** | 🔴 **只有 5 级！** 而任务清单有 8 个任务、4 个优先级档，够用但必须精打细算（见第五节） |
| `configUSE_PREEMPTION` | 1 | 抢占式，硬实时必需 |
| `configUSE_MUTEXES` | 1 | 共享外设（UART/CNN）要互斥 |
| `configUSE_TICKLESS_IDLE` | **被注释掉了** | ⭐ **本项目的关键**：哨兵要省电，必须打开并实现 `vPortSuppressTicksAndSleep`（demo 已给出可用实现） |
| `configUSE_TRACE_FACILITY` / `configUSE_STATS_FORMATTING_FUNCTIONS` | 1 | 任务运行统计，配合 `FreeRTOS_Debug.c` 的 TMR0 |
| `INCLUDE_vTaskSuspend` / `vTaskDelayUntil` / `vTaskDelay` | 1 | 用到的都开着 |
| `INCLUDE_vTaskDelete` / `vTaskPrioritySet` / `uxTaskPriorityGet` | **0** | 🔴 若要做"按需创建/销毁深层推理任务"或动态调优先级，**必须改成 1** |
| `configKERNEL_INTERRUPT_PRIORITY` | `7 << 5` | 最低优先级 |
| `configMAX_SYSCALL_INTERRUPT_PRIORITY` | `5 << 5` | 🔴 **中断优先级 ≥ 5 的 ISR 不许调 FreeRTOS API**（`...FromISR`）。MAX78000 只用高 3 位优先级——**这条最容易踩** |
| `DEBUG=1` 时的 `configASSERT` | 死循环 | 调试期留着，发布版务必关 |

### 中断 ↔ RTOS 的三条铁律

1. **ISR 里只能用 `...FromISR` 版本** API（`vTaskNotifyGiveFromISR`、`xQueueSendFromISR`…）。
2. 用完必须 `portYIELD_FROM_ISR(xHigherPriorityTaskWoken)`，否则高优先级任务要等下一个 tick 才跑。
3. **NVIC 优先级数值必须 ≥ `configMAX_SYSCALL_INTERRUPT_PRIORITY`（demo 里是 5）**，
   即**数字越大优先级越低**。设成 0~4 的 ISR 一调 RTOS API 就会 `configASSERT` 挂掉。
   demo 里 `NVIC_SetPriority(UARTx_IRQn, 1)` —— 注意这是 **1（高优先级）**，
   所以那个 ISR **只调了 `MXC_UART_AsyncHandler` 和 `wutHitSnooze`**，
   真正调 `vTaskNotifyGiveFromISR` 的是 UART 驱动内部经回调转发的 `vCmdLineTask_cb`（`main.c` L206）。

---

## 五、8 个任务落到 demo 骨架上

本项目规划的 8 个任务（见 `../../进展总结.md` 第七节）映射到 5 个优先级档：

| 任务 | 建议优先级 | 触发方式 | 参考 demo 写法 |
|---|---:|---|---|
| 1 音频采集 | `tskIDLE_PRIORITY + 4`（最高） | **I2S DMA 半满/全满中断** | `vCmdLineTask_cb`（ISR → 任务通知） |
| 2 前处理（折叠量化） | `+3` | 采集任务给信号量/通知 | `vTask0`（`vTaskDelayUntil` 周期任务） |
| 3 哨兵推理 | `+3` | 前处理完成 | 需自建互斥量保护 CNN 加速器 |
| 4 门控决策 | `+3` | 哨兵完成 | 纯计算，可直接内联在 3 里 |
| 5 深层推理 | `+2`（按需唤醒） | 门控判异常 → 通知 | `vCmdLineTask`（`ulTaskNotifyTake` 阻塞等唤醒） |
| 6 结果处理 | `+2` | 深层完成 | 纯计算 |
| 7 串口通讯 | `+2` | 双向：UART 中断收 / 队列发 | `vCmdLineTask` + `MXC_UART_TransactionAsync` |
| 8 缓存管理 | `+1`（低） | 周期 + 事件 | `vTickTockTask`（`vTaskDelayUntil` 长周期） |

**必备的同步原语（demo 里都有现成写法）：**

| 用途 | 用什么 | demo 出处 |
|---|---|---|
| 保护 UART / CNN 加速器 | 二值互斥量 `xSemaphoreCreateMutex()` | `main.c` L411 `xGPIOmutex` |
| ISR → 任务 唤醒（推荐，最省内存） | 任务通知 `vTaskNotifyGiveFromISR` / `ulTaskNotifyTake` | `main.c` L212 / L269 |
| DMA 缓冲双向交接 | 两个静态缓冲 + 队列传指针，或直接双缓冲裸指针 | 需自建 |
| 结果上报 | 队列 `xQueueSend` | — |

> ⚠ **CNN 加速器是单实例硬件**，哨兵推理和深层推理**不能并行**，必须用互斥量串行化。
> 好在两者都只要 39 µs / 122 µs，串行完全够用。

---

## 六、tickless idle：低功耗的落地点

`freertos_tickless.c` 提供了**可直接复用**的实现，要点：

| 机制 | 说明 |
|---|---|
| 为什么需要 | 进 DEEPSLEEP 后 **SysTick 停摆**，没法靠它唤醒 |
| 怎么解决 | 进睡眠前用 **WUT** 排一个未来的中断，靠 WUT 中断把 WFI 打断 |
| 守门函数 | `freertos_permit_tickless()` —— **你需要重写它**：有 UART/SPI/I2C 在传输时返回非 `E_NO_ERROR` 阻止睡眠 |
| 最小睡眠阈值 | `MIN_WUT_TICKS = 50`，不够就只进普通 sleep |
| 最长睡眠钳位 | `MAX_WUT_SNOOZE = 5 × 32768`（5 秒） |
| 唤醒源配置 | `MXC_LP_EnableWUTAlarmWakeup()` + `MXC_LP_EnableGPIOWakeup(&pin)` |

**本项目对应做法**：把 `freertos_permit_tickless()` 重写成"当 I2S DMA 正在采集 或 CNN 正在推理时，
返回 `E_BUSY` 不睡；其余空闲时间就放心睡"。

启用方式：取消 `FreeRTOSConfig.h` 里 `#define configUSE_TICKLESS_IDLE 1` 的注释，
并实现 `vPreSleepProcessing` / `vPostSleepProcessing`（demo 已留好钩子）。

---

## 七、调试设施（多任务必用）

来自 `FreeRTOS_Debug.c`，`project.mk` 里 `DEBUG=1` 时生效：

| 设施 | 作用 |
|---|---|
| `ConfigTimerForStats()` / `GetTimerForStats()` | 用 **TMR0** 做 32 kHz 运行统计定时器，支撑 `vTaskGetRunTimeStats()` 看每个任务占了多少 CPU |
| `prvGetRegistersFromStack()` + `HardFault_Handler` | 把 HardFault 现场的寄存器**存进 C 变量**，可在调试器里直接看 PC/LR，配合反汇编定位崩点 |
| `vApplicationStackOverflowHook` | 任务栈溢出时抓现场 |

> ⚠ demo README 提醒：**TMR0 在低功耗模式下可能工作异常**，跑 tickless 时统计定时器要换成低功耗域定时器。

**查栈够不够**的实用手段：`uxTaskGetStackHighWaterMark(NULL)` 返回任务生命周期内栈的最小剩余量。

---

## 八、常见坑（提前记下）

| 坑 | 现象 | 对策 |
|---|---|---|
| 在优先级 < 5 的 ISR 里调 RTOS API | `configASSERT` 死循环 / 随机死机 | NVIC 优先级数值必须 ≥ 5 |
| 忘记 `portYIELD_FROM_ISR` | 高优先级任务延迟一个 tick 才响应 | ISR 末尾补上 |
| 动态创建任务/队列把 26 KB 堆耗尽 | `pvPortMalloc` 返回 NULL，任务创建失败 | 用 `xTaskCreateStatic` / 静态队列；音频缓冲用全局数组 |
| 从 ISR 里 `printf` | 阻塞、乱序、甚至死锁 | 只往队列塞，让任务去打 |
| UART 异步事务忘了实现 IRQHandler 调 `MXC_UART_AsyncHandler` | 回调永不触发，任务永远阻塞 | 参照 `FreeRTOSDemo/main.c` L193 |
| `configUSE_TICKLESS_IDLE=1` 但没实现 `freertos_permit_tickless` | 传输中被睡眠打断，数据错乱 | 必须在有外设活动时返回非 0 |
| 上电直接按 100 MHz 算 tick | 时间基准错 | 先 `MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO)` + `SystemCoreClockUpdate()` |
| `INCLUDE_vTaskDelete=0` 还想删任务 | 编译期 `vTaskDelete` 未定义 | 改 `FreeRTOSConfig.h` 为 1 |
| 两个任务同时用 CNN 加速器 | 权重/数据被覆盖，结果乱 | 互斥量串行化 |

---

## 九、下一步（本项目）

1. **抄骨架**：以 `MAX78000_FreeRTOSDemo` 为基底新建工程，改 `FreeRTOSConfig.h`（堆、优先级、tickless、`INCLUDE_vTaskDelete`）。
2. **先跑通最小闭环**：1 个采集任务 + 1 个推理任务 + 1 个串口任务，验证 I2S→折叠→CNN→UART 全链路。
3. **再加门控与低功耗**：接上质心门控，打开 tickless，实测空载电流。
4. **最后补全 8 任务**：加缓存管理、看门狗、异常恢复。
5. **实测项**：各任务栈高水位、CPU 占用率（`vTaskGetRunTimeStats`）、空载/满载电流。

---

## 十、参考

| 资源 | 位置 |
|---|---|
| MSDK 用户指南 | <https://analogdevicesinc.github.io/msdk/USERGUIDE/> |
| FreeRTOS 官方文档 | <https://www.freertos.org/Documentation/RTOS_book.html> |
| 本机 SDK 范例 | `D:\MaximSDK\Examples\MAX78000\FreeRTOSDemo\` |
| 内核源码 | `D:\MaximSDK\Libraries\FreeRTOS\` |
| 外设 API 查表 | [`../03_api/README.md`](../03_api/README.md) |
| 两个已交付模型 | [`../01_models/README.md`](../01_models/README.md) |
