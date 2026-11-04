# `rtc.h` — RTC 实时时钟

> **概要**：Real Time Clock (RTC) functions and prototypes.
> **头文件**：`03_api/headers/rtc.h`
> **驱动实现**：`03_api/source_ai85/RTC/`
> **函数** 19　**宏** 2　**枚举** 3　**结构体** 0　**全局变量** 0

---

## 目录

- [枚举类型](#枚举类型)
- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 枚举类型

### `mxc_rtc_freq_sel_t`

| 成员 | 说明 |
|---|---|
| `MXC_RTC_F_1HZ = MXC_S_RTC_CTRL_SQW_SEL_FREQ1HZ` | 1Hz (Compensated) |
| `MXC_RTC_F_512HZ = MXC_S_RTC_CTRL_SQW_SEL_FREQ512HZ` | 512Hz (Compensated) |
| `MXC_RTC_F_4KHZ = MXC_S_RTC_CTRL_SQW_SEL_FREQ4KHZ` | 4Khz |
| `MXC_RTC_F_32KHZ = 32` | 32Khz |

### `mxc_rtc_int_en_t`

| 成员 | 说明 |
|---|---|
| `MXC_RTC_INT_EN_LONG = MXC_F_RTC_CTRL_TOD_ALARM_IE` | Long-interval alarm interrupt enable |
| `MXC_RTC_INT_EN_SHORT = MXC_F_RTC_CTRL_SSEC_ALARM_IE` | Short-interval alarm interrupt enable |
| `MXC_RTC_INT_EN_READY = MXC_F_RTC_CTRL_RDY_IE` | Timer ready interrupt enable |

### `mxc_rtc_int_fl_t`

| 成员 | 说明 |
|---|---|
| `MXC_RTC_INT_FL_LONG = MXC_F_RTC_CTRL_TOD_ALARM` | Long-interval alarm interrupt flag |
| `MXC_RTC_INT_FL_SHORT = MXC_F_RTC_CTRL_SSEC_ALARM` | Short-interval alarm interrupt flag |
| `MXC_RTC_INT_FL_READY = MXC_F_RTC_CTRL_RDY` | Timer ready interrupt flag |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_RTC_MAX_SSEC` | `(MXC_F_RTC_SSEC_SSEC + 1)` |  |
| `MXC_RTC_TRIM_TMR_IRQ` | `0x0` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_RTC_SetTimeofdayAlarm(uint32_t ras)` | Set Time-of-Day alarm value and enable Interrupt |
| `int MXC_RTC_SetSubsecondAlarm(uint32_t rssa)` | Set Sub-Second alarm value and enable interrupt, |
| `int MXC_RTC_Start(void)` | Start the Real Time Clock (Blocking function) |
| `int MXC_RTC_Stop(void)` | Stop the Real Time Clock (Blocking function) |
| `int MXC_RTC_Init(uint32_t sec, uint16_t ssec)` | Initialize the sec and ssec registers and enable RTC (Blocking function)　*⚠ If you wish to manage clock configuration externally, define the flag MSDK_NO_GPIO_CLK_INIT.* |
| `int MXC_RTC_SquareWaveStart(mxc_rtc_freq_sel_t fq)` | Allow generation of Square Wave on the SQW pin (Blocking function)　*⚠ If you wish to manage GPIO configuration externally, define the flag MSDK_NO_GPIO_CLK_INIT.* |
| `int MXC_RTC_SquareWaveStop(void)` | Stop the generation of square wave (Blocking function) |
| `int MXC_RTC_Trim(int8_t trm)` | Set Trim register value (Blocking function) |
| `int MXC_RTC_EnableInt(uint32_t mask)` | Enable Interurpts (Blocking function) |
| `int MXC_RTC_DisableInt(uint32_t mask)` | Disable Interurpts (Blocking function) |
| `int MXC_RTC_GetFlags(void)` | Gets interrupt flags. |
| `int MXC_RTC_ClearFlags(int flags)` | Clear interrupt flags. |
| `int MXC_RTC_GetSubSecond(void)` | Get SubSecond or E_BUSY, see /ref MXC_ERROR_CODES　***已废弃**：Use MXC_RTC_GetSubSeconds() instead.* |
| `int MXC_RTC_GetSubSeconds(uint32_t *ssec)` | This function stores the current value of the sub-seconds counter into a pointer if the RTC is not busy. If the RTC is busy, an error is returned. |
| `int MXC_RTC_GetSecond(void)` | Get Second or E_BUSY, see /ref MXC_ERROR_CODES　***已废弃**：Use MXC_RTC_GetSeconds() instead.* |
| `int MXC_RTC_GetSeconds(uint32_t *sec)` | This function stores the current value of the seconds counter into a pointer if the RTC is not busy. If the RTC is busy, an error is returned. |
| `int MXC_RTC_GetTime(uint32_t *sec, uint32_t *subsec)` | Get the current second and sub-second counts. |
| `int MXC_RTC_GetBusyFlag(void)` | Get RTC busy flag. |
| `int MXC_RTC_TrimCrystal(void)` | Use the 32 MHz crystal to trim the 32 kHz crystal. |

## 依赖的其他头文件

- `stdint.h`
- `mxc_device.h`
- `rtc_regs.h`
- `mxc_sys.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `rtc.h` 自动生成，请勿手改；改脚本后重跑。*
