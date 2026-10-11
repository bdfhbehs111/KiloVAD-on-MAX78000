# `tmr.h` — TMR 通用定时器

> **概要**：Timer (TMR) function prototypes and data types.
> **头文件**：`03_api/headers/tmr.h`
> **驱动实现**：`03_api/source_ai85/TMR/`
> **函数** 28　**宏** 0　**枚举** 5　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [typedef](#typedef)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_tmr_cfg_t`

| 字段 | 说明 |
|---|---|
| `mxc_tmr_pres_t pres` | Desired timer prescaler |
| `mxc_tmr_mode_t mode` | Desired timer mode |
| `mxc_tmr_bit_mode_t bitMode` | Desired timer bits |
| `mxc_tmr_clock_t clock` | Desired clock source |
| `uint32_t cmp_cnt` | Compare register value in timer ticks |
| `unsigned pol` | Polarity (0 or 1) |

## 枚举类型

### `mxc_tmr_pres_t`

| 成员 | 说明 |
|---|---|
| `MXC_TMR_PRES_1 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_1` | Divide input clock by 1 |
| `MXC_TMR_PRES_2 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_2` | Divide input clock by 2 |
| `MXC_TMR_PRES_4 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_4` | Divide input clock by 4 |
| `MXC_TMR_PRES_8 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_8` | Divide input clock by 8 |
| `MXC_TMR_PRES_16 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_16` | Divide input clock by 16 |
| `MXC_TMR_PRES_32 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_32` | Divide input clock by 32 |
| `MXC_TMR_PRES_64 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_64` | Divide input clock by 64 |
| `MXC_TMR_PRES_128 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_128` | Divide input clock by 128 |
| `MXC_TMR_PRES_256 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_256` | Divide input clock by 256 |
| `MXC_TMR_PRES_512 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_512` | Divide input clock by 512 |
| `MXC_TMR_PRES_1024 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_1024` | Divide input clock by 1024 |
| `MXC_TMR_PRES_2048 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_2048` | Divide input clock by 2048 |
| `MXC_TMR_PRES_4096 = MXC_S_TMR_CTRL0_CLKDIV_A_DIV_BY_4096` | Divide input clock by 4096 |
| `TMR_PRES_1 = MXC_TMR_PRES_1` | Legacy names |
| `TMR_PRES_2 = MXC_TMR_PRES_2` |  |
| `TMR_PRES_4 = MXC_TMR_PRES_4` |  |
| `TMR_PRES_8 = MXC_TMR_PRES_8` |  |
| `TMR_PRES_16 = MXC_TMR_PRES_16` |  |
| `TMR_PRES_32 = MXC_TMR_PRES_32` |  |
| `TMR_PRES_64 = MXC_TMR_PRES_64` |  |
| `TMR_PRES_128 = MXC_TMR_PRES_128` |  |
| `TMR_PRES_256 = MXC_TMR_PRES_256` |  |
| `TMR_PRES_512 = MXC_TMR_PRES_512` |  |
| `TMR_PRES_1024 = MXC_TMR_PRES_1024` |  |
| `TMR_PRES_2048 = MXC_TMR_PRES_2048` |  |
| `TMR_PRES_4096 = MXC_TMR_PRES_4096` |  |

### `mxc_tmr_mode_t`

| 成员 | 说明 |
|---|---|
| `MXC_TMR_MODE_ONESHOT = MXC_V_TMR_CTRL0_MODE_A_ONE_SHOT` | Timer Mode ONESHOT |
| `MXC_TMR_MODE_CONTINUOUS = MXC_V_TMR_CTRL0_MODE_A_CONTINUOUS` | Timer Mode CONTINUOUS |
| `MXC_TMR_MODE_COUNTER = MXC_V_TMR_CTRL0_MODE_A_COUNTER` | Timer Mode COUNTER |
| `MXC_TMR_MODE_PWM = MXC_V_TMR_CTRL0_MODE_A_PWM` | Timer Mode PWM |
| `MXC_TMR_MODE_CAPTURE = MXC_V_TMR_CTRL0_MODE_A_CAPTURE` | Timer Mode CAPTURE |
| `MXC_TMR_MODE_COMPARE = MXC_V_TMR_CTRL0_MODE_A_COMPARE` | Timer Mode COMPARE |
| `MXC_TMR_MODE_GATED = MXC_V_TMR_CTRL0_MODE_A_GATED` | Timer Mode GATED |
| `MXC_TMR_MODE_CAPTURE_COMPARE = MXC_V_TMR_CTRL0_MODE_A_CAPCOMP` | Timer Mode CAPTURECOMPARE |
| `MXC_TMR_MODE_DUAL_EDGE = MXC_V_TMR_CTRL0_MODE_A_DUAL_EDGE` | Timer Mode DUALEDGE |
| `TMR_MODE_ONESHOT = MXC_TMR_MODE_ONESHOT` | Legacy names |
| `TMR_MODE_CONTINUOUS = MXC_TMR_MODE_CONTINUOUS` |  |
| `TMR_MODE_COUNTER = MXC_TMR_MODE_COUNTER` |  |
| `TMR_MODE_PWM = MXC_TMR_MODE_PWM` |  |
| `TMR_MODE_CAPTURE = MXC_TMR_MODE_CAPTURE` |  |
| `TMR_MODE_COMPARE = MXC_TMR_MODE_COMPARE` |  |
| `TMR_MODE_GATED = MXC_TMR_MODE_GATED` |  |
| `TMR_MODE_CAPTURE_COMPARE = MXC_TMR_MODE_CAPTURE_COMPARE` |  |
| `TMR_MODE_DUAL_EDGE = MXC_TMR_MODE_DUAL_EDGE` |  |

### `mxc_tmr_bit_mode_t`

| 成员 | 说明 |
|---|---|
| `MXC_TMR_BIT_MODE_32 = 0` | Timer Mode 32 bit |
| `MXC_TMR_BIT_MODE_16A` | Timer Mode Lower 16 bit |
| `MXC_TMR_BIT_MODE_16B` | Timer Mode Upper 16 bit |
| `TMR_BIT_MODE_32 = MXC_TMR_BIT_MODE_32` | Legacy names |
| `TMR_BIT_MODE_16A = MXC_TMR_BIT_MODE_16A` |  |
| `TMR_BIT_MODE_16B = MXC_TMR_BIT_MODE_16B` |  |

### `mxc_tmr_unit_t`

| 成员 | 说明 |
|---|---|
| `MXC_TMR_UNIT_NANOSEC = 0` | Nanosecond Unit Indicator |
| `MXC_TMR_UNIT_MICROSEC` | Microsecond Unit Indicator |
| `MXC_TMR_UNIT_MILLISEC` | Millisecond Unit Indicator |
| `MXC_TMR_UNIT_SEC` | Second Unit Indicator |
| `TMR_UNIT_NANOSEC = MXC_TMR_UNIT_NANOSEC` | Legacy names |
| `TMR_UNIT_MICROSEC = MXC_TMR_UNIT_MICROSEC` |  |
| `TMR_UNIT_MILLISEC = MXC_TMR_UNIT_MILLISEC` |  |
| `TMR_UNIT_SEC = MXC_TMR_UNIT_SEC` |  |

### `mxc_tmr_clock_t`

| 成员 | 说明 |
|---|---|
| `MXC_TMR_APB_CLK = 0` | PCLK |
| `MXC_TMR_EXT_CLK = 1` | External Clock |
| `MXC_TMR_ISO_CLK = 2` | 60MHz Clock |
| `MXC_TMR_IBRO_CLK = 3` | 7.3728MHz Clock |
| `MXC_TMR_ERTCO_CLK = 4` | 32.768KHz Clock |
| `MXC_TMR_INRO_CLK = 5` | 8-30KHz Clock |
| `MXC_TMR_IBRO_DIV8_CLK = 6` | (7.3728/8)MHz Clock |
| `MXC_TMR_60M_CLK = MXC_TMR_ISO_CLK` | 8M and 60M clocks can be used for Timers 0,1,2 and 3 |
| `MXC_TMR_8M_CLK = MXC_TMR_IBRO_CLK` |  |
| `MXC_TMR_32K_CLK = MXC_TMR_ERTCO_CLK` | 32K clock can be used for Timers 0,1,2,3 and 4 |
| `MXC_TMR_8K_CLK = MXC_TMR_INRO_CLK` | 8K and EXT clocks can only be used for Timers 4 and 5 |
| `MXC_TMR_8M_DIV8_CLK = MXC_TMR_IBRO_DIV8_CLK` |  |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_tmr_complete_t` | `void (*mxc_tmr_complete_t)(int error)` |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_TMR_Init(mxc_tmr_regs_t *tmr, mxc_tmr_cfg_t *cfg, bool init_pins)` | Initialize timer module clock.　*⚠ On default this function enables TMR peripheral clock and related GPIOs. if you wish to manage clock and gpio related things in upper level instead of here. Define MSDK_NO_GPIO_CLK_INIT flag in project.mk file. By this flag this function will remove clock and gpio related codes from file.* |
| `void MXC_TMR_SetClockSourceFreq(mxc_tmr_regs_t *tmr, int clksrc_freq)` | Set the timer input clock frequency.　*⚠ Call this after selecting MXC_TMR_EXT_CLK on RevB timers. This API has no effect on timer revisions without selectable clock sources.* |
| `void MXC_TMR_Shutdown(mxc_tmr_regs_t *tmr)` | Shutdown timer module clock. |
| `void MXC_TMR_Start(mxc_tmr_regs_t *tmr)` | Start the timer counting. |
| `void MXC_TMR_Stop(mxc_tmr_regs_t *tmr)` | Stop the timer. |
| `int MXC_TMR_SetPWM(mxc_tmr_regs_t *tmr, uint32_t pwm)` | Set the value of the first transition in PWM mode　*⚠ Will block until safe to change the period count.* |
| `uint32_t MXC_TMR_GetCompare(mxc_tmr_regs_t *tmr)` | Get the timer compare count. |
| `uint32_t MXC_TMR_GetCapture(mxc_tmr_regs_t *tmr)` | Get the timer capture count. |
| `uint32_t MXC_TMR_GetCount(mxc_tmr_regs_t *tmr)` | Get the timer count. |
| `uint32_t MXC_TMR_GetPeriod(mxc_tmr_regs_t *tmr, mxc_tmr_clock_t clock, uint32_t prescalar, uint32_t frequency)` | Calculate count for required frequency. |
| `void MXC_TMR_ClearFlags(mxc_tmr_regs_t *tmr)` | Clear the timer interrupt. |
| `uint32_t MXC_TMR_GetFlags(mxc_tmr_regs_t *tmr)` | Get the timer interrupt status. |
| `void MXC_TMR_EnableInt(mxc_tmr_regs_t *tmr)` | enable interupt |
| `void MXC_TMR_DisableInt(mxc_tmr_regs_t *tmr)` | disable interupt |
| `void MXC_TMR_EnableWakeup(mxc_tmr_regs_t *tmr, mxc_tmr_cfg_t *cfg)` | Enable wakeup from sleep |
| `void MXC_TMR_DisableWakeup(mxc_tmr_regs_t *tmr, mxc_tmr_cfg_t *cfg)` | Disable wakeup from sleep |
| `void MXC_TMR_SetCompare(mxc_tmr_regs_t *tmr, uint32_t cmp_cnt)` | Set the timer compare count.　*⚠ In PWM Mode use this to set the value of the second transition.* |
| `void MXC_TMR_SetCount(mxc_tmr_regs_t *tmr, uint32_t cnt)` | Set the timer count. |
| `void MXC_TMR_Delay(mxc_tmr_regs_t *tmr, uint32_t us)` | Dealay for a set periord of time measured in microseconds |
| `void MXC_TMR_TO_Start(mxc_tmr_regs_t *tmr, uint32_t us)` | Start a timer that will time out after a certain number of microseconds |
| `int MXC_TMR_TO_Check(mxc_tmr_regs_t *tmr)` | Check on time out timer |
| `void MXC_TMR_TO_Stop(mxc_tmr_regs_t *tmr)` | Stop the Timeout timer |
| `void MXC_TMR_TO_Clear(mxc_tmr_regs_t *tmr)` | Clear timeout timer back to zero |
| `unsigned int MXC_TMR_TO_Elapsed(mxc_tmr_regs_t *tmr)` | Get elapsed time of timeout timer |
| `unsigned int MXC_TMR_TO_Remaining(mxc_tmr_regs_t *tmr)` | Amount of time remaining until timeour |
| `void MXC_TMR_SW_Start(mxc_tmr_regs_t *tmr)` | Start stopwatch |
| `unsigned int MXC_TMR_SW_Stop(mxc_tmr_regs_t *tmr)` | Stopwatch stop |
| `int MXC_TMR_GetTime(mxc_tmr_regs_t *tmr, uint32_t ticks, uint32_t *time, mxc_tmr_unit_t *units)` | Get time from timer |

## 依赖的其他头文件

- `stdint.h`
- `stdbool.h`
- `mxc_device.h`
- `tmr_regs.h`
- `mxc_sys.h`
- `gcr_regs.h`
- `mcr_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `tmr.h` 自动生成，请勿手改；改脚本后重跑。*
