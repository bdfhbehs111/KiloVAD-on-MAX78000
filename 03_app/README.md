# 04_app —— MAX78000 应用工程【模板】

本目录是「创建模板」的产物：**只有基础设施，没有一行应用代码。**

---

## 一、目录内容

| 文件 | 来源 | 作用 |
|---|---|---|
| `Makefile` | MSDK 原厂核心 Makefile（与原厂逐字节一致） | 编译规则。**不要编辑**，配置写进 `project.mk` |
| `project.mk` | 本模板新写 | 挂库 / 指定链接脚本 / 优化开关 |
| `max78000_app.ld` | 原厂 `max78000.ld` 逐字节副本 + 内存注释 | 链接脚本（内存布局的权威） |
| `FreeRTOSConfig.h` | 原厂 FreeRTOSDemo 副本 + 2 处改动 | FreeRTOS 配置 |
| `README.md` | 本文件 | 说明 |

**注意**：核心 Makefile 会自动 glob 本目录（及 `VPATH`）里所有 `*.c`。
所以以后加文件只需放进本目录，不用改任何 Makefile。

---

## 二、模板做了什么 / 故意没做什么

### 做了（准备工作）
- 内存布局：`max78000_app.ld`，并在 `project.mk` 里用 `LINKERFILE` 挂上
- 库接入：FreeRTOS（`LIB_FREERTOS=1`、heap_4、`RTOS_CONFIG_DIR=.`）+ 外设驱动/BSP（MSDK 默认已开）
- 构建：接进仓库根的 CMake 编排（`CMakeLists.txt` 里已注册 `app 04_app BOARD FTHR_RevA`）
- 工具链发现、`BOARD` 默认值、`DEBUG` 开关

### 故意没做（属于你的决策）
- ❌ `main.c`（连文件都不建）
- ❌ FreeRTOS 创建几个任务、优先级、栈深
- ❌ 在哪里拉起任务（`xTaskCreate` 的位置与数量）
- ❌ 任何 `struct` / `typedef` / `enum`
- ❌ 任务函数体、ISR、任何业务逻辑
- ❌ 队列 / 信号量 / 互斥量 / 任务通知的创建
- ❌ 全局变量、配置宏、缓冲区

原因：这些是**设计决策**，不是**准备工作**。

---

## 三、内存布局（`max78000_app.ld`）

| 区域 | 起始 | 长度 | 大小 | 用途 |
|---|---|---|---|---|
| ROM | `0x00000000` | `0x00010000` | 64 KiB | 片内 ROM |
| FLASH | `0x10000000` | `0x00080000` | 512 KiB | 代码 + `.rodata` + `.data` 初值 |
| **SRAM** | `0x20000000` | `0x0001FF80` | **130,944 B** | `.data`/`.bss`/`.heap`/`.stack` 全在这 |
| SHARED | `0x2001FF80` | `0x00000080` | 128 B | 双核共享区 |

**这是单核 ARM 布局：M4F 独占 130,944 B SRAM。**

> ⚠ 如果哪天改用双核（`Examples/MAX78000/CNN/kws20_demo-riscv` 那套），链接脚本会换成
> `max78000_arm.ld`，它 include 的 `common.ld` 把 SRAM 劈成
> `SRAM0 32K(.data/.bss)` + `SRAM1 32K(.heap/.stack)` + `SRAM2 48K(RV)` + `SRAM3 16K(RV)`
> —— **M4F 可用量腰斩到 64 KiB**。这是个重大决定，别顺手做。

链接器暴露的符号（可 `extern` 引用）：`_bss`/`_ebss`、`_data`/`_edata`、`__load_data`、
`_shared`/`_eshared`、`__StackTop`、`__HeapLimit`。

两条 `ASSERT` 会在**编译期**拦住超预算：
```
region RAM overflowed with stack     ← .data/.bss/.heap/.stack 超了 SRAM
.shared section overflow             ← SHARED 区超 128 B
```

要在 SRAM 里预留固定区域（例如给某个池子一个已知地址），在 `max78000_app.ld` 里加一个
`NOLOAD` 段放在 `.bss` 之后即可，脚本顶部注释里有现成例子。

---

## 四、`FreeRTOSConfig.h` 相对原厂的两处改动

其余数值与原厂**逐字相同**。改动都写了理由：

| # | 改动 | 为什么 |
|---|---|---|
| 1 | 把「运行时间统计」从 `DEBUG` 开关里摘出来，默认关闭（新增 `USE_RUN_TIME_STATS`） | 原厂 `#if defined(DEBUG) && DEBUG == 1` 会打开 `configGENERATE_RUN_TIME_STATS`，而它要求实现 `ConfigTimerForStats()`/`GetTimerForStats()`（应用代码）。而 `gcc.mk:443-444` 在 `DEBUG!=0` 时会加 `-DDEBUG` → **`DEBUG=1` 直接链接失败**。要用就打开宏并自己实现那两个函数 |
| 2 | `configASSERT` 无条件打开 | 原厂把它放在 `DEBUG==1` 里 → `DEBUG=0` 时 FreeRTOS 的所有内部检查全部消失。这对查 bug 太伤了 |

文件里所有**策略项**都标了注释：`configMAX_PRIORITIES`、`configTOTAL_HEAP_SIZE`、
`INCLUDE_vTask*`、`configUSE_TRACE_FACILITY`、`configTICK_RATE_HZ`。要改直接改。

---

## 五、两处原厂坑（都已规避）

### 1. `BOARD ?=` 是空操作
核心 Makefile 的顺序是 `BOARD ?= EvKit_V1`（第 62 行）→ 才 include `project.mk`（第 94 行）。
所以 `project.mk` 里写 `BOARD ?= FTHR_RevA` **不会生效**，直接 `make` 会静默编成 EvKit 版
（无板载麦克风）。本模板用 `BOARD = FTHR_RevA` 规避。

### 2. `LINKERFILE` 没有搜索路径
`gcc.mk:686` 把它**原样**传给 `-T`（只在 MSYS 下过一遍 `cygpath`），
所以必须是相对文件名或绝对路径。本模板用相对名 `max78000_app.ld`。

---

## 六、怎么编译

在**仓库根目录**（`project_sys_agent_max78000/`）：

```bash
cmake -S . -B build -G Ninja                 # 首次配置（默认 MAXIM_PATH=D:/MaximSDK）
cmake --build build --target app             # 编本工程
cmake --build build --target app-rebuild     # 清理后重编
cmake --build build --target app-size        # Flash/SRAM 占用
cmake --build build --target list-targets    # 全部可用目标
```

也可以绕过 CMake 直接编（需要设好 PATH 和 `MAXIM_PATH`）：
```bash
cd 04_app
make TARGET=MAX78000 BOARD=FTHR_RevA MAXIM_PATH=D:/MaximSDK
```

---

## 七、你现在要写的第一步

模板里**没有** `main.c`，所以现在编出来会在链接期报 `undefined reference to 'main'`。
这是**预期的**——入口点是你的决策。

最小可以这样起（新建 `04_app/main.c`）：

```c
#include "mxc.h"

int main(void)
{
    MXC_ICC_Enable(MXC_ICC0);
    MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO);   /* 上电默认 60 MHz，必须切 100 MHz */
    SystemCoreClockUpdate();

    /* ================================================================
     *  ↓↓↓  以下全部由你决定  ↓↓↓
     *  - 创建几个任务、优先级、栈深
     *  - 结构体 / 枚举 / 全局量
     *  - 在哪里 xTaskCreate、队列/信号量怎么建
     *  - vTaskStartScheduler() 放哪
     * ================================================================ */

    for (;;) { }
}
```

---

## 八、参考（本机 MSDK 路径）

| 用途 | 路径 |
|---|---|
| FreeRTOS 集成范例 | `D:\MaximSDK\Examples\MAX78000\FreeRTOSDemo` |
| 麦克风 + 裸 FIFO 中断 | `D:\MaximSDK\Examples\MAX78000\I2S` |
| 麦克风 + DMA | `D:\MaximSDK\Examples\MAX78000\I2S_DMA`、`I2S_DMA_Target` |
| 麦克风 + 模型（ARM） | `D:\MaximSDK\Examples\MAX78000\CNN\kws20_demo` |
| 麦克风 + 模型（RISC-V） | `D:\MaximSDK\Examples\MAX78000\CNN\kws20_demo-riscv` |
| 本工程核心 Makefile 原版 | `D:\MaximSDK\Examples\MAX78000\FreeRTOSDemo\Makefile` |
| 本工程链接脚本原版 | `D:\MaximSDK\Libraries\CMSIS\Device\Maxim\MAX78000\Source\GCC\max78000.ld` |

仓库内其他参考：`02_rtos/`（FreeRTOS 内核源码）、`03_api/`（外设 API 文档与头文件）、
`01_models/`（两个模型的权重与独立验证工程）。
---

## 九、⚠ 一个原厂默认【关闭】但强烈建议打开的选项

原厂 `FreeRTOSConfig.h` **没有**定义下面这两个，FreeRTOS 会默认按 0 处理：

| 选项 | 默认 | 打开后你需要提供 |
|---|---|---|
| `configCHECK_FOR_STACK_OVERFLOW 2` | 0（关） | `void vApplicationStackOverflowHook(TaskHandle_t, char *)` |
| `configUSE_MALLOC_FAILED_HOOK 1` | 0（关） | `void vApplicationMallocFailedHook(void)` |

**栈溢出是嵌入式 RTOS 最常见的崩溃原因**，而关掉它意味着栈被写穿时你什么都看不到
（表现为随机的 HardFault 或数据被静默改写）。

打开方式：在 `FreeRTOSConfig.h` 里加这两行，并在你自己的某个 `.c` 里实现那两个钩子。
**钩子是应用代码，所以本模板不提供** —— 这是你的决策。

参考实现（放在你自己的文件里）：

```c
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    printf("\n*** STACK OVERFLOW: %s ***\n", pcTaskName ? pcTaskName : "?");
    taskDISABLE_INTERRUPTS();
    for (;;) { }
}

void vApplicationMallocFailedHook(void)
{
    printf("\n*** MALLOC FAILED ***\n");
    taskDISABLE_INTERRUPTS();
    for (;;) { }
}
```

另外两个同样默认关闭、但排查时很有用的：`configUSE_IDLE_HOOK`、`configUSE_TICK_HOOK`。