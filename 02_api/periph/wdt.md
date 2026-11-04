# `wdt.h` — WDT 看门狗

> **概要**：Watchdog timer (WDT) function prototypes and data types.
> **头文件**：`03_api/headers/wdt.h`
> **驱动实现**：`03_api/source_ai85/WDT/`
> **函数** 16　**宏** 0　**枚举** 5　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_wdt_cfg_t`

| 字段 | 说明 |
|---|---|
| `mxc_wdt_mode_t mode` | WDT mode |
| `mxc_wdt_period_t upperResetPeriod` | Reset upper limit |
| `mxc_wdt_period_t lowerResetPeriod` | Reset lower limit |
| `mxc_wdt_period_t upperIntPeriod` | Interrupt upper limit |
| `mxc_wdt_period_t lowerIntPeriod` | Interrupt lower limit |

## 枚举类型

### `mxc_wdt_period_t`

| 成员 | 说明 |
|---|---|
| `MXC_WDT_PERIOD_2_31 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW31` | Period 2^31 |
| `MXC_WDT_PERIOD_2_30 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW30` | Period 2^30 |
| `MXC_WDT_PERIOD_2_29 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW29` | Period 2^29 |
| `MXC_WDT_PERIOD_2_28 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW28` | Period 2^28 |
| `MXC_WDT_PERIOD_2_27 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW27` | Period 2^27 |
| `MXC_WDT_PERIOD_2_26 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW26` | Period 2^26 |
| `MXC_WDT_PERIOD_2_25 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW25` | Period 2^25 |
| `MXC_WDT_PERIOD_2_24 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW24` | Period 2^24 |
| `MXC_WDT_PERIOD_2_23 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW23` | Period 2^23 |
| `MXC_WDT_PERIOD_2_22 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW22` | Period 2^22 |
| `MXC_WDT_PERIOD_2_21 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW21` | Period 2^21 |
| `MXC_WDT_PERIOD_2_20 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW20` | Period 2^20 |
| `MXC_WDT_PERIOD_2_19 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW19` | Period 2^19 |
| `MXC_WDT_PERIOD_2_18 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW18` | Period 2^18 |
| `MXC_WDT_PERIOD_2_17 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW17` | Period 2^17 |
| `MXC_WDT_PERIOD_2_16 = MXC_S_WDT_CTRL_INT_LATE_VAL_WDT2POW16` | Period 2^16 |

### `mxc_wdt_int_t`

| 成员 | 说明 |
|---|---|
| `MXC_WDT_INT_TOO_LATE = MXC_F_WDT_CTRL_INT_LATE` |  |
| `MXC_WDT_INT_TOO_SOON = MXC_F_WDT_CTRL_INT_EARLY` |  |

### `mxc_wdt_rst_t`

| 成员 | 说明 |
|---|---|
| `MXC_WDT_RST_TOO_LATE = MXC_F_WDT_CTRL_RST_LATE` |  |
| `MXC_WDT_RST_TOO_SOON = MXC_F_WDT_CTRL_RST_EARLY` |  |

### `mxc_wdt_mode_t`

| 成员 | 说明 |
|---|---|
| `MXC_WDT_COMPATIBILITY = 0` |  |
| `MXC_WDT_WINDOWED = 1` |  |

### `mxc_wdt_clock_t`

| 成员 | 说明 |
|---|---|
| `MXC_WDT_PCLK = 0` |  |
| `MXC_WDT_IBRO_CLK` |  |
| `MXC_WDT_INRO_CLK` |  |
| `MXC_WDT_ERTCO_CLK` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_WDT_Init(mxc_wdt_regs_t *wdt, mxc_wdt_cfg_t *cfg)` | Initialize the Watchdog Timer　*⚠ On default this function enables WDT peripheral clock. if you wish to manage clock and gpio related things in upper level instead of here. Define MSDK_NO_GPIO_CLK_INIT flag in project.mk file. By this flag this function will remove clock and gpio related codes from file.* |
| `int MXC_WDT_Shutdown(mxc_wdt_regs_t *wdt)` | Shutdown the Watchdog Timer |
| `void MXC_WDT_SetIntPeriod(mxc_wdt_regs_t *wdt, mxc_wdt_cfg_t *cfg)` | Set the period of the watchdog interrupt. |
| `void MXC_WDT_SetResetPeriod(mxc_wdt_regs_t *wdt, mxc_wdt_cfg_t *cfg)` | Set the period of the watchdog reset. |
| `void MXC_WDT_Enable(mxc_wdt_regs_t *wdt)` | Enable the watchdog timer. |
| `void MXC_WDT_Disable(mxc_wdt_regs_t *wdt)` | Disable the watchdog timer. |
| `void MXC_WDT_EnableInt(mxc_wdt_regs_t *wdt)` | Enable the watchdog interrupt. |
| `void MXC_WDT_DisableInt(mxc_wdt_regs_t *wdt)` | Disable the watchdog interrupt. |
| `void MXC_WDT_EnableReset(mxc_wdt_regs_t *wdt)` | Enable the watchdog reset. |
| `void MXC_WDT_DisableReset(mxc_wdt_regs_t *wdt)` | Disable the watchdog reset. |
| `void MXC_WDT_ResetTimer(mxc_wdt_regs_t *wdt)` | Reset the watchdog timer. |
| `int MXC_WDT_GetResetFlag(mxc_wdt_regs_t *wdt)` | Get the status of the reset flag. |
| `void MXC_WDT_ClearResetFlag(mxc_wdt_regs_t *wdt)` | Clears the reset flag. |
| `int MXC_WDT_GetIntFlag(mxc_wdt_regs_t *wdt)` | Get the status of the interrupt flag. |
| `void MXC_WDT_ClearIntFlag(mxc_wdt_regs_t *wdt)` | Clears the interrupt flag. |
| `int MXC_WDT_SetClockSource(mxc_wdt_regs_t *wdt, mxc_wdt_clock_t clock_source)` | Sets clock source. |

## 依赖的其他头文件

- `stdint.h`
- `mxc_device.h`
- `wdt_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `wdt.h` 自动生成，请勿手改；改脚本后重跑。*
