# `wut.h` — WUT 唤醒定时器

> **概要**：Wakeup Timer (WUT) function prototypes and data types.
> **头文件**：`03_api/headers/wut.h`
> **驱动实现**：`03_api/source_ai85/WUT/`
> **函数** 22　**宏** 0　**枚举** 3　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [typedef](#typedef)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_wut_cfg_t`

| 字段 | 说明 |
|---|---|
| `mxc_wut_mode_t mode` | Desired timer mode |
| `uint32_t cmp_cnt` | Compare register value in timer ticks |

## 枚举类型

### `mxc_wut_pres_t`

| 成员 | 说明 |
|---|---|
| `MXC_WUT_PRES_1 = MXC_S_WUT_CTRL_PRES_DIV1` | Divide input clock by 1 |
| `MXC_WUT_PRES_2 = MXC_S_WUT_CTRL_PRES_DIV2` | Divide input clock by 2 |
| `MXC_WUT_PRES_4 = MXC_S_WUT_CTRL_PRES_DIV4` | Divide input clock by 4 |
| `MXC_WUT_PRES_8 = MXC_S_WUT_CTRL_PRES_DIV8` | Divide input clock by 8 |
| `MXC_WUT_PRES_16 = MXC_S_WUT_CTRL_PRES_DIV16` | Divide input clock by 16 |
| `MXC_WUT_PRES_32 = MXC_S_WUT_CTRL_PRES_DIV32` | Divide input clock by 32 |
| `MXC_WUT_PRES_64 = MXC_S_WUT_CTRL_PRES_DIV64` | Divide input clock by 64 |
| `MXC_WUT_PRES_128 = MXC_S_WUT_CTRL_PRES_DIV128` | Divide input clock by 128 |
| `MXC_WUT_PRES_256 = MXC_F_WUT_CTRL_PRES3 \| MXC_S_WUT_CTRL_PRES_DIV1` | Divide input clock by 256 |
| `MXC_WUT_PRES_512 = MXC_F_WUT_CTRL_PRES3 \| MXC_S_WUT_CTRL_PRES_DIV2` | Divide input clock by 512 |
| `MXC_WUT_PRES_1024 = MXC_F_WUT_CTRL_PRES3 \| MXC_S_WUT_CTRL_PRES_DIV4` | Divide input clock by 1024 |
| `MXC_WUT_PRES_2048 = MXC_F_WUT_CTRL_PRES3 \| MXC_S_WUT_CTRL_PRES_DIV8` | Divide input clock by 2048 |
| `MXC_WUT_PRES_4096 = MXC_F_WUT_CTRL_PRES3 \| MXC_S_WUT_CTRL_PRES_DIV16` | Divide input clock by 4096 |

### `mxc_wut_mode_t`

| 成员 | 说明 |
|---|---|
| `MXC_WUT_MODE_ONESHOT = MXC_V_WUT_CTRL_TMODE_ONESHOT` | Wakeup Timer Mode ONESHOT |
| `MXC_WUT_MODE_CONTINUOUS = MXC_V_WUT_CTRL_TMODE_CONTINUOUS` | Wakeup Timer Mode CONTINUOUS |
| `MXC_WUT_MODE_COUNTER = MXC_V_WUT_CTRL_TMODE_COUNTER` | Wakeup Timer Mode COUNTER |
| `MXC_WUT_MODE_CAPTURE = MXC_V_WUT_CTRL_TMODE_CAPTURE` | Wakeup Timer Mode CAPTURE |
| `MXC_WUT_MODE_COMPARE = MXC_V_WUT_CTRL_TMODE_COMPARE` | Wakeup Timer Mode COMPARE |
| `MXC_WUT_MODE_GATED = MXC_V_WUT_CTRL_TMODE_GATED` | Wakeup Timer Mode GATED |
| `MXC_WUT_MODE_CAPTURE_COMPARE = MXC_V_WUT_CTRL_TMODE_CAPTURECOMPARE` | Wakeup Timer Mode CAPTURECOMPARE |

### `mxc_wut_unit_t`

| 成员 | 说明 |
|---|---|
| `MXC_WUT_UNIT_NANOSEC = 0` | Nanosecond Unit Indicator. |
| `MXC_WUT_UNIT_MICROSEC` | Microsecond Unit Indicator. |
| `MXC_WUT_UNIT_MILLISEC` | Millisecond Unit Indicator. Second Unit Indicator. |
| `MXC_WUT_UNIT_SEC` |  |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_wut_complete_cb_t` | `void (*mxc_wut_complete_cb_t)(int result)` |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `void MXC_WUT_Init(mxc_wut_pres_t pres)` | Initialize timer module clock. |
| `void MXC_WUT_Shutdown(void)` | Shutdown timer module clock. |
| `void MXC_WUT_Enable(void)` | Enable the timer. |
| `void MXC_WUT_Disable(void)` | Disable the timer. |
| `void MXC_WUT_Config(const mxc_wut_cfg_t *cfg)` | Configure the timer. |
| `uint32_t MXC_WUT_GetCompare(void)` | Get the timer compare count. |
| `uint32_t MXC_WUT_GetCount(void)` | Get the timer count. |
| `void MXC_WUT_IntClear(void)` | Clear the timer interrupt.　***已废弃**：Use MXC_WUT_ClearFlags instead.  See wut.h for more details.* |
| `void MXC_WUT_ClearFlags(void)` | Clear the timer interrupt. |
| `uint32_t MXC_WUT_IntStatus(void)` | Get the timer interrupt status.　***已废弃**：Use MXC_WUT_GetFlags instead.  See wut.h for more details.* |
| `uint32_t MXC_WUT_GetFlags(void)` | Get the timer interrupt status. |
| `void MXC_WUT_SetCompare(uint32_t cmp_cnt)` | Set the timer compare count.　*⚠ This function does not protect against output glitches in PWM mode. Use MXC_WUT_PWMSetPeriod when in PWM mode.* |
| `void MXC_WUT_SetCount(uint32_t cnt)` | Set the timer count. |
| `int MXC_WUT_GetTicks(uint32_t time, mxc_wut_unit_t units, uint32_t *ticks)` | Convert real time to timer ticks. |
| `int MXC_WUT_GetTime(uint32_t ticks, uint32_t *time, mxc_wut_unit_t *units)` | Convert timer ticks to real time. |
| `void MXC_WUT_Edge(void)` | Wait for an edge of the WUT count register.　***已废弃**：Use MXC_WUT_WaitForEdge instead.  See wut.h for more details.* |
| `void MXC_WUT_WaitForEdge(void)` | Wait for an edge of the WUT count register. |
| `void MXC_WUT_Store(void)` | Store the count and snapshot values.　***已废弃**：Use MXC_WUT_StoreCount instead.  See wut.h for more details.* |
| `void MXC_WUT_StoreCount(void)` | Store the count and snapshot values. |
| `void MXC_WUT_RestoreBBClock(uint32_t dbbFreq)` | Restore the DBB clock with the stored count and snapshot values. |
| `uint32_t MXC_WUT_GetSleepTicks(void)` | Get the difference between the stored counter value and the current counter value. |
| `void MXC_WUT_Delay_MS(uint32_t waitMs)` | Delays for the given number of milliseconds. |

## 依赖的其他头文件

- `mxc_device.h`
- `wut_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `wut.h` 自动生成，请勿手改；改脚本后重跑。*
