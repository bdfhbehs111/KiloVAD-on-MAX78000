# 03_api — MAX78000 外设标准库 API 查表

> 目的：**不用翻 872 个源文件、4 万字头文件**，一页纸查完某个外设的全部函数、结构体、枚举、宏。

---

## 一、目录结构

| 路径 | 内容 | 规模 |
|---|---|---|
| `periph/` | ⭐ **按外设拆分的速查表（31 篇）** — 主要就查这里 | 159 KB |
| `_global_functions.md` | ⭐ **545 个函数总表**（字母序，函数名 → 外设 → 头文件） | 38 KB |
| `_index.json` | 机器可读索引（程序化查表 / 让 AI 读） | 170 KB |
| `_periph_summary.md` | 外设统计表 | 3 KB |
| `headers/` | **31 个外设驱动头文件**（MSDK 官方原件，权威依据） | 313 KB |
| `headers_cmsis/` | **38 个寄存器/器件头文件**（`*_regs.h`、`max78000.h`、`SystemInit`） | 969 KB |
| `source_ai85/` | **MAX78000 驱动实现源码子集**（`*_ai85.c` + 各 rev + common） | 2.3 MB |
| `startup_gcc/` | 启动汇编、链接脚本、`heap.c`（**排 RTOS 堆栈时要看**） | 62 KB |
| `tools/gen_api_docs.py` | 速查表生成脚本（SDK 升级后重跑） | — |

> `periph/`、`_index.json`、`_global_functions.md`、`_periph_summary.md` 都是**脚本生成**的，
> 不要手改；改脚本后重跑即可。

---

## 二、三种查法

### 1. 知道外设 → 直接开速查表
```
periph/uart.md      periph/gpio.md     periph/tmr.md
periph/wut.md       periph/i2s.md      periph/dma.md
periph/lp.md        periph/mxc_sys.md  ...
```
每篇包含：**结构体字段 / 枚举成员 / 宏 / 预定义全局变量 / 函数（按官方章节分组，带 `@brief` 中文摘录）**。

### 2. 知道函数名 → 搜总表
打开 `_global_functions.md`，`Ctrl+F` 搜函数名，立刻知道它在哪个外设、哪个头文件。

### 3. 程序化查 → 读 JSON
```python
import json
idx = json.load(open("_index.json", encoding="utf-8"))
[f for f in idx if f["name"].startswith("MXC_UART_Transaction")]
# -> [{"name": ..., "proto": ..., "brief": ..., "header": "uart.h", "periph": "uart", ...}]
```

---

## 三、命名规律（查表时靠这个猜名字）

| 形态 | 含义 | 例子 |
|---|---|---|
| `MXC_<外设>_<动作>` | 外设函数 | `MXC_UART_Init`、`MXC_GPIO_Config` |
| `mxc_<外设>_cfg_t` | **配置**结构体（初始化时填） | `mxc_tmr_cfg_t`、`mxc_wut_cfg_t` |
| `mxc_<外设>_req_t` | **事务**结构体（异步/DMA 用） | `mxc_uart_req_t`、`mxc_spi_req_t` |
| `gpio_cfg_<外设><n>` | SDK 预定义引脚配置，**直接用不用自己填** | `gpio_cfg_uart0`、`gpio_cfg_i2c0` |
| `MXC_GPIO_PORT_<n>` / `MXC_GPIO_PIN_<n>` | 端口/引脚位掩码 | `MXC_GPIO_PIN_12` |
| `MXC_<外设>_<寄存器>_<字段>` | 寄存器位域掩码 | 见下 |
| `E_*` | 返回错误码 | `E_NO_ERROR`(0)、`E_BUSY`(-6) |

### 寄存器位域三级宏（`headers_cmsis/*_regs.h`）
| 前缀 | 含义 |
|---|---|
| `MXC_F_<REG>_<FIELD>` | 字段**掩码**（已移位） |
| `MXC_F_<REG>_<FIELD>_POS` | 字段**起始位** |
| `MXC_S_<REG>_<FIELD>` | 字段**移位量** |
| `MXC_V_<REG>_<FIELD>_<值名>` | 字段**枚举值**（已就位） |

### 返回值约定
绝大多数 `int` 返回函数用 `E_*`：`0` 成功，**负数是错误**。完整表见 [`periph/mxc_errors.md`](periph/mxc_errors.md)。

| 码 | 值 | 码 | 值 |
|---|---:|---|---:|
| `E_NO_ERROR` / `E_SUCCESS` | 0 | `E_COMM_ERR` | −9 |
| `E_NULL_PTR` | −1 | `E_TIME_OUT` | −10 |
| `E_BAD_PARAM` | −3 | `E_OVERFLOW` | −12 |
| `E_UNINITIALIZED` | −5 | `E_NOT_SUPPORTED` | −17 |
| `E_BUSY` | −6 | `E_FAIL` | −255 |

---

## 四、典型调用序列（**抄自官方 Example，非杜撰**）

> 每个片段都能在 `D:\MaximSDK\Examples\MAX78000\<外设>\main.c` 找到原版。

### 0) 开机基线：开缓存 + 选 100 MHz 主频
```c
#include "mxc.h"          // 总入口，一个头文件拉通所有外设
MXC_ICC_Enable(MXC_ICC0);                  // 开指令缓存 —— 100MHz 下必开，否则性能腰斩
MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO);   // 内部主振 100MHz
SystemCoreClockUpdate();
```
> 出处：`Examples\MAX78000\I2S_DMA\main.c`

### 1) GPIO 输出（点灯 / 片选 / 唤醒线）
```c
mxc_gpio_cfg_t led;
led.port   = MXC_GPIO0;              // 端口常量是 MXC_GPIO0..3，位掩码宏才是 MXC_GPIO_PORT_0
led.mask   = MXC_GPIO_PIN_2;
led.pad    = MXC_GPIO_PAD_NONE;
led.func   = MXC_GPIO_FUNC_OUT;
led.vssel  = MXC_GPIO_VSSEL_VDDIO;   // VDDIO 域；跨域要选 MXC_GPIO_VSSEL_VDDIOH
led.drvstr = MXC_GPIO_DRVSTR_0;
MXC_GPIO_Config(&led);
MXC_GPIO_OutSet(led.port, led.mask); // 或 OutClr / OutToggle / Out
```
> 出处：`Examples\MAX78000\GPIO\main.c`

### 2) GPIO 输入 + 中断（按键 / 外部唤醒）
```c
gpio_in.pad  = MXC_GPIO_PAD_PULL_UP;     // 按键接地，用上拉
gpio_in.func = MXC_GPIO_FUNC_IN;
MXC_GPIO_Config(&gpio_in);

MXC_GPIO_RegisterCallback(&gpio_in, my_isr, &ctx);
MXC_GPIO_IntConfig(&gpio_in, MXC_GPIO_INT_FALLING);
MXC_GPIO_EnableInt(gpio_in.port, gpio_in.mask);
NVIC_EnableIRQ(MXC_GPIO_GET_IRQ(MXC_GPIO_GET_IDX(gpio_in.port)));
```
> 出处：`Examples\MAX78000\GPIO\main.c`。ISR 里记得 `MXC_GPIO_ClearFlags(port)`。

### 3) UART 阻塞式
```c
int err = MXC_UART_Init(MXC_UART_GET_UART(0), 115200, MXC_UART_APB_CLK);
MXC_UART_Write(MXC_UART_GET_UART(0), buf, &len);
```
> 出处：`Examples\MAX78000\UART\main.c`

### 4) UART 异步事务（**RTOS 推荐用法**，不阻塞任务）
```c
mxc_uart_req_t req;
req.uart     = ConsoleUART;
req.rxData   = &tmp;      req.rxLen = 1;
req.txData   = NULL;      req.txLen = 0;
req.callback = on_char;   // void (*)(mxc_uart_req_t *, int)

MXC_UART_TransactionAsync(&req);
// ISR 里必须调用，否则回调不会触发：
void UARTx_IRQHandler(void) { MXC_UART_AsyncHandler(ConsoleUART); }
```
> 出处：`Examples\MAX78000\FreeRTOSDemo\main.c`（配合 `ulTaskNotifyTake` / `vTaskNotifyGiveFromISR` 唤醒任务）

### 5) TMR 周期中断（RTOS 节拍 / 喂狗 / 采样节拍）
```c
mxc_tmr_cfg_t tmr;
tmr.pres    = MXC_TMR_PRES_128;
tmr.mode    = MXC_TMR_MODE_CONTINUOUS;
tmr.bitMode = MXC_TMR_BIT_MODE_32;
tmr.clock   = MXC_TMR_IBRO_CLK;                                     // 7.3728 MHz
tmr.cmp_cnt = MXC_TMR_GetPeriod(MXC_TMR0, MXC_TMR_IBRO_CLK, 128, 1000); // 1 kHz
tmr.pol     = 0;

MXC_TMR_Init(MXC_TMR0, &tmr, true);   // 第三参 init_pins = 是否顺手把引脚也配好
MXC_TMR_EnableInt(MXC_TMR0);
MXC_TMR_Start(MXC_TMR0);
```
> 出处：`Examples\MAX78000\TMR\main.c`
> 实例名是 **`MXC_TMR0` ~ `MXC_TMR5`**（不是 `TMR0`）。TMR4/5 是低功耗域，只能用
> 8K/32K/EXT 时钟；TMR0~3 可用 60M/8M。
> 枚举有 `MXC_` 前缀的新名和 `TMR_` 前缀的 **legacy 旧名**两套，新代码用前者。

### 6) WUT 唤醒定时器（**哨兵低功耗的核心**）
```c
mxc_wut_cfg_t cfg;
uint32_t ticks;
MXC_WUT_GetTicks(1000, MXC_WUT_UNIT_MILLISEC, &ticks);  // 1 秒

cfg.mode    = MXC_WUT_MODE_ONESHOT;    // 或 MXC_WUT_MODE_COMPARE
cfg.cmp_cnt = ticks;

MXC_WUT_Init(MXC_WUT_PRES_1);
MXC_WUT_Config(&cfg);
MXC_LP_EnableWUTAlarmWakeup();         // 注册为唤醒源
NVIC_EnableIRQ(WUT_IRQn);
MXC_WUT_Enable();
MXC_LP_EnterSleepMode();               // 睡下去，WUT 到点唤醒
```
> 出处：`Examples\MAX78000\WUT\main.c`。`Examples\MAX78000\FreeRTOSDemo\freertos_tickless.c`
> 是**可运行的 tickless 范例**：用 WUT 替代停摆的 SysTick 来唤醒深度睡眠。

### 7) DMA（内存搬运 / 外设 FIFO）
```c
MXC_DMA_Init();
int ch = MXC_DMA_AcquireChannel();

mxc_dma_config_t config;
config.reqsel   = MXC_DMA_REQUEST_MEMTOMEM;  // 外设搬运改这里（见 mxc_dma_reqsel_t）
config.srcwd    = MXC_DMA_WIDTH_WORD;
config.dstwd    = MXC_DMA_WIDTH_WORD;
config.srcinc_en = 1;
config.dstinc_en = 1;

mxc_dma_srcdst_t xfer;
xfer.source = src;  xfer.dest = dst;  xfer.len = bytes;

mxc_dma_adv_config_t adv;
adv.prio  = MXC_DMA_PRIO_HIGH;
adv.pssel = MXC_DMA_PRESCALE_DISABLE;
adv.tosel = MXC_DMA_TIMEOUT_4_CLK;

MXC_DMA_ConfigChannel(config, xfer);
MXC_DMA_AdvConfigChannel(adv);
MXC_DMA_SetCallback(ch, my_cb);   // void (*)(int ch, int error)
MXC_DMA_EnableInt(ch);
MXC_DMA_Start(ch);
// ISR 里必须调用：MXC_DMA_Handler();
```
> 出处：`Examples\MAX78000\DMA\main.c`。一次性拷贝可用 `MXC_DMA_MemCpy(dst, src, len, cb)`。

### 8) I2S + DMA 采麦克风（**音频采集任务的核心**）
```c
mxc_i2s_req_t req;
req.wordSize    = MXC_I2S_WSIZE_WORD;
req.sampleSize  = MXC_I2S_SAMPLESIZE_THIRTYTWO;  // ⚠ 32 位！不是 16
req.bitsWord    = 32;                            // ⚠ 32 位！不是 16
req.adjust      = MXC_I2S_ADJUST_LEFT;
req.justify     = MXC_I2S_MSB_JUSTIFY;
req.wsPolarity  = MXC_I2S_POL_NORMAL;
req.channelMode = MXC_I2S_INTERNAL_SCK_WS_0;
req.stereoMode  = MXC_I2S_MONO_LEFT_CH;         // 板载麦克风只有左声道
req.bitOrder    = MXC_I2S_MSB_FIRST;
req.clkdiv      = MXC_I2S_CalculateClockDiv(16000, req.wordSize, 12288000);

MXC_I2S_Init(&req);
MXC_I2S_SetRXThreshold(4);
MXC_I2S_RegisterDMACallback(on_half_full);
MXC_I2S_RXDMAConfig(rx_buf, sizeof(rx_buf));   // rx_buf 必须是 uint32_t[]！
```

> ⚠⚠ **板载麦克风是 32 位字、有效数据在高 18 位**，不是 16 位。
> 官方 `kws20_demo`（麦克风喂 CNN 的范例）原话：
> `/* The actual value is 18 MSB of 32-bit word */` → `temp = sample >> 14;`
> 所以 DMA 缓冲必须是 `uint32_t`，取 16 位样本要右移 14。
> 详见 [`../04_app/README.md`](../04_app/README.md) 第五节的位宽表和推导。
> 出处：`Examples\MAX78000\I2S_DMA\main.c`
> ⚠ FTHR 板要先给麦克风上电：`max20303_mic_power(1)`（经 I2C1 控制 PMIC）。

### 9) 低功耗模式切换（功耗从浅到深）
```c
MXC_LP_EnableWUTAlarmWakeup();                  // 先注册唤醒源
MXC_LP_EnableGPIOWakeup(&wakeup_pin);
MXC_LP_EnableRTCAlarmWakeup();

MXC_LP_EnterSleepMode();        // 最浅，CPU 停，外设全活
MXC_LP_EnterLowPowerMode();     // 关部分时钟
MXC_LP_EnterMicroPowerMode();   // 更深，靠 32k 时钟
MXC_LP_EnterStandbyMode();      // 只留备份域
MXC_LP_EnterPowerDownMode();    // 不返回！靠 RTC/USB/GPIO 唤醒后重启
MXC_LP_EnterBackupMode();       // 最深，不返回
```
> 出处：`Examples\MAX78000\LP\main.c`。**注意最后两个"不返回"**，用之前必须先把状态存进备份寄存器或 Flash。

### 10) 外设时钟门控（省电的关键 —— 不用的外设要关掉）
```c
MXC_SYS_ClockEnable(MXC_SYS_PERIPH_CLOCK_I2S);     // 开某外设时钟（注意：ClockEnable 无下划线）
MXC_SYS_ClockDisable(MXC_SYS_PERIPH_CLOCK_I2S);    // 关掉省电
MXC_SYS_IsClockEnabled(MXC_SYS_PERIPH_CLOCK_I2S);  // 查状态
MXC_SYS_Reset_Periph(MXC_SYS_RESET1_I2S);          // 复位外设（注意是 RESET1）
```
> 枚举全集见 [`periph/mxc_sys.md`](periph/mxc_sys.md)。
> ⚠ `MXC_SYS_RESET0_*` 与 `MXC_SYS_RESET1_*` 是**两组**复位寄存器，别选错；
> `MXC_SYS_RESET_*`（无数字）是第三组（LP 域）。

---

## 五、本项目（sys_agent）任务 → 该查哪页

| RTOS 任务 | 主要外设 | 查这些页 |
|---|---|---|
| 1 音频采集 | **I2S + DMA + ICC** | [`i2s.md`](periph/i2s.md) [`dma.md`](periph/dma.md) [`icc.md`](periph/icc.md) |
| 2 前处理 | 纯 CPU（定点折叠） | [`mxc_sys.md`](periph/mxc_sys.md)（主频/缓存） |
| 3 哨兵推理 | **CNN 加速器** | 不走 PeriphDrivers，见 `01_models/*/max78000/*/cnn.c` |
| 4 门控决策 | 纯 CPU | — |
| 5 深层推理 | **CNN 加速器 + ICC** | 同上 |
| 6 结果处理 | 纯 CPU | — |
| 7 串口通讯 | **UART（异步事务）** | [`uart.md`](periph/uart.md) [`nvic_table.md`](periph/nvic_table.md) |
| 8 缓存管理 | **LP / WUT / RTC** | [`lp.md`](periph/lp.md) [`wut.md`](periph/wut.md) [`rtc.md`](periph/rtc.md) |
| — 看门狗兜底 | **WDT** | [`wdt.md`](periph/wdt.md) |
| — 临界区 | SYS 内联函数 | [`mxc_sys.md`](periph/mxc_sys.md)（`MXC_SYS_Crit_Enter/Exit`、`MXC_CRITICAL`） |
| — 核间通信（可选） | **ICC + SEMA** | [`icc.md`](periph/icc.md) [`sema.md`](periph/sema.md) |

---

## 六、外设统计表

| 外设 | 头文件 | 中文名 | 函数 | 宏 | 枚举 | 结构体 | 速查表 |
|---|---|---|---:|---:|---:|---:|---|
| `i2c` | `i2c.h` | I2C 总线 | 52 | 4 | 1 | 1 | [i2c.md](periph/i2c.md) |
| `uart` | `uart.h` | UART 串口 | 51 | 1 | 4 | 1 | [uart.md](periph/uart.md) |
| `spi` | `spi.h` | SPI 总线 | 43 | 0 | 2 | 2 | [spi.md](periph/spi.md) |
| `lp` | `lp.h` | LP 低功耗电源管理 | 34 | 0 | 2 | 0 | [lp.md](periph/lp.md) |
| `owm` | `owm.h` | OWM 单总线 | 34 | 7 | 1 | 1 | [owm.md](periph/owm.md) |
| `adc` | `adc.h` | ADC | 32 | 17 | 5 | 2 | [adc.md](periph/adc.md) |
| `tmr` | `tmr.h` | TMR 通用定时器 | 28 | 0 | 5 | 1 | [tmr.md](periph/tmr.md) |
| `i2s` | `i2s.h` | I2S 音频接口 | 26 | 5 | 7 | 1 | [i2s.md](periph/i2s.md) |
| `gpio` | `gpio.h` | GPIO | 25 | 36 | 7 | 1 | [gpio.md](periph/gpio.md) |
| `dma` | `dma.h` | DMA | 24 | 0 | 5 | 3 | [dma.md](periph/dma.md) |
| `aes` | `aes.h` | AES 加解密 | 23 | 0 | 2 | 1 | [aes.md](periph/aes.md) |
| `wut` | `wut.h` | WUT 唤醒定时器 | 22 | 0 | 3 | 1 | [wut.md](periph/wut.md) |
| `mxc_sys` | `mxc_sys.h` | 系统时钟/复位/外设使能 | 21 | 4 | 4 | 1 | [mxc_sys.md](periph/mxc_sys.md) |
| `rtc` | `rtc.h` | RTC 实时时钟 | 19 | 2 | 3 | 0 | [rtc.md](periph/rtc.md) |
| `flc` | `flc.h` | FLC 闪存控制器 | 16 | 2 | 0 | 0 | [flc.md](periph/flc.md) |
| `wdt` | `wdt.h` | WDT 看门狗 | 16 | 0 | 5 | 1 | [wdt.md](periph/wdt.md) |
| `pt` | `pt.h` | PT 脉冲序列发生器 | 15 | 0 | 1 | 1 | [pt.md](periph/pt.md) |
| `crc` | `crc.h` | CRC 校验 | 12 | 0 | 1 | 1 | [crc.md](periph/crc.md) |
| `trng` | `trng.h` | TRNG 真随机数 | 10 | 0 | 0 | 0 | [trng.md](periph/trng.md) |
| `cameraif` | `cameraif.h` | CameraIF 摄像头接口 | 9 | 0 | 4 | 0 | [cameraif.md](periph/cameraif.md) |
| `icc` | `icc.h` | ICC 双核通信 | 7 | 0 | 1 | 0 | [icc.md](periph/icc.md) |
| `lpcmp` | `lpcmp.h` | LPCMP 比较器 | 7 | 0 | 2 | 0 | [lpcmp.md](periph/lpcmp.md) |
| `sema` | `sema.h` | SEMA 硬件信号量 | 6 | 0 | 0 | 0 | [sema.md](periph/sema.md) |
| `mxc_delay` | `mxc_delay.h` | 阻塞延时 | 5 | 3 | 0 | 0 | [mxc_delay.md](periph/mxc_delay.md) |
| `nvic_table` | `nvic_table.h` | NVIC 向量表 | 5 | 0 | 0 | 0 | [nvic_table.md](periph/nvic_table.md) |
| `mxc_lock` | `mxc_lock.h` | 自旋锁 | 2 | 0 | 0 | 0 | [mxc_lock.md](periph/mxc_lock.md) |
| `mxc_assert` | `mxc_assert.h` | 断言 | 1 | 4 | 0 | 0 | [mxc_assert.md](periph/mxc_assert.md) |
| 其他 | `mxc.h` `mxc_device.h` `mxc_errors.h` `mxc_pins.h` | 总入口/器件/错误码/引脚 | 0 | 25 | 0 | 0 | — |
| **合计** | **31 个头文件** | | **545** | **110** | **65** | **19** | |

---

## 七、重新生成速查表

SDK 升级后（`D:\MaximSDK` 更新），按顺序重跑：

```powershell
# 1. 重新拷贝头文件（可选，若 SDK 有更新）
Copy-Item "D:\MaximSDK\Libraries\PeriphDrivers\Include\MAX78000\*" `
          "<本目录>\headers" -Force

# 2. 重新生成
$env:PYTHONIOENCODING="utf-8"
& "C:\Users\13157\AppData\Local\Programs\Python\Python311\python.exe" `
  "<本目录>\tools\gen_api_docs.py"
```

脚本会打印 **函数总数**、**无函数声明的头文件**、**缺 `@brief` 的函数**，可据此判断是否解析异常
（正常情况下缺 `@brief` 的应为 3 个：`_mxc_crit_get_state`、`NVIC_SetVector`、`NVIC_GetVector`）。

---

## 八、已知局限（脚本是正则解析，不是编译器）

| 局限 | 影响 | 说明 |
|---|---|---|
| 条件编译分支合并 | 同名函数只留说明最全的一条 | 如 `mxc_delay.h` 的 RISC-V/ARM 两分支，会标注「多核分支重复声明，已合并」 |
| 宏的值截断到 60 字符 | 超长宏看不全 | 需要完整定义请查 `headers/` 原件 |
| 不含 `static` 函数体逻辑 | 只知道签名和一句说明 | 需要看实现请查 `source_ai85/` |
| 不解析 `#if` 分支的互斥关系 | 可能同时看到互斥的常量 | 以头文件原件为准 |
| CMSIS 寄存器头文件未生成速查表 | 只有 `.h` 原件 | 位域宏数量太大（上万），直接搜 `headers_cmsis/` 更快 |

**权威依据永远是 `headers/` 里的官方原件**；速查表只是索引和摘要。
