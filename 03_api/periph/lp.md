# `lp.h` — LP 低功耗电源管理

> **概要**：Low Power(LP) function prototypes and data types.
> **头文件**：`03_api/headers/lp.h`
> **驱动实现**：`03_api/source_ai85/LP/`
> **函数** 34　**宏** 0　**枚举** 2　**结构体** 0　**全局变量** 0

---

## 目录

- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 枚举类型

### `mxc_lp_ovr_t`

| 成员 | 说明 |
|---|---|
| `MXC_LP_V0_9 = 0` |  |
| `MXC_LP_V1_0` |  |
| `MXC_LP_V1_1` |  |

### `mxc_lp_cfg_ds_pd_t`

| 成员 | 说明 |
|---|---|
| `MXC_LP_IPO = MXC_F_GCR_PM_IPO_PD` |  |
| `MXC_LP_IBRO = MXC_F_GCR_PM_IBRO_PD` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `void MXC_LP_EnterSleepMode(void)` | Places the device into SLEEP mode. This function returns once an RTC or external interrupt occur. |
| `void MXC_LP_EnterLowPowerMode(void)` | Places the device into Low Power mode. This function returns once an RTC or external interrupt occur. |
| `void MXC_LP_EnterMicroPowerMode(void)` | Places the device into Micro Power mode. This function returns once an RTC or external interrupt occur. |
| `void MXC_LP_EnterStandbyMode(void)` | Places the device into Standby mode. This function returns once an RTC or external interrupt occur. |
| `void MXC_LP_EnterBackupMode(void)` | Places the device into BACKUP mode. CPU state is not maintained in this mode, so this function never returns. Instead, the device will restart once an RTC or external interrupt occur. |
| `void MXC_LP_EnterPowerDownMode(void)` | Places the device into Shutdown mode. CPU state is not maintained in this mode, so this function never returns. Instead, the device will restart once an RTC, USB wakeup, or external interrupt occur. |
| `void MXC_LP_SetOVR(mxc_lp_ovr_t ovr)` | Set ovr bits to set the voltage the micro will run at. |
| `void MXC_LP_BandgapOn(void)` | Turn bandgap on |
| `void MXC_LP_BandgapOff(void)` | Turn bandgap off |
| `int MXC_LP_BandgapIsOn(void)` | Is the bandgap on or off |
| `int MXC_LP_IsBackupWake(void)` | Returns 1 if device wakes up from BACKUP mode. |
| `void MXC_LP_ClearWakeStatus(void)` | clear all wake up status |
| `void MXC_LP_EnableGPIOWakeup(mxc_gpio_cfg_t *wu_pins)` | Enables the selected GPIO port and its selected pins to wake up the device from any low power mode. Call this function multiple times to enable pins on multiple ports. This function does not configure the GPIO pins nor does it setup their interrupt functionality. |
| `void MXC_LP_DisableGPIOWakeup(mxc_gpio_cfg_t *wu_pins)` | Disables the selected GPIO port and its selected pins as a wake up source. Call this function multiple times to disable pins on multiple ports. |
| `uint32_t MXC_LP_GetGPIOWakeupEnable(uint8_t port)` | Get the enabled wakeup pins for a specific GPIO port. Returns 0 if the port is not present on the device. |
| `uint32_t MXC_LP_GetGPIOWakeupStatus(uint8_t port)` | Get the wakeup status of a specific GPIO port. Returns 0 if the port is not present on the device. |
| `void MXC_LP_ClearGPIOWakeupStatus(uint8_t port, uint32_t mask)` | Clear the wakeup status of a specific GPIO port. Does nothing if the port is not present on the device. |
| `void MXC_LP_EnableRTCAlarmWakeup(void)` | Enables the RTC alarm to wake up the device from any low power mode. |
| `void MXC_LP_DisableRTCAlarmWakeup(void)` | Disables the RTC alarm from waking up the device. |
| `void MXC_LP_EnableTimerWakeup(mxc_tmr_regs_t *tmr)` | Enables Timer to wakeup from any low power mode. |
| `void MXC_LP_DisableTimerWakeup(mxc_tmr_regs_t *tmr)` | Disables Timer from waking up device. |
| `void MXC_LP_EnableWUTAlarmWakeup(void)` | Enables the WUT alarm to wake up the device from any low power mode. |
| `void MXC_LP_DisableWUTAlarmWakeup(void)` | Disables the WUT alarm from waking up the device. |
| `void MXC_LP_EnableLPCMPWakeup(mxc_lpcmp_cmpsel_t cmp)` | Enables the LPCMP to wake up the device from any low power mode. |
| `void MXC_LP_DisableLPCMPWakeup(mxc_lpcmp_cmpsel_t cmp)` | Disables the LPCMP from waking up the device. |
| `int MXC_LP_ConfigDeepSleepClocks(uint32_t mask)` | Configure which clocks are powered down at deep sleep and which are not affected.　*⚠ Need to configure all clocks at once any clock not passed in the mask will be unaffected by Deepsleep. This will always overwrite the previous settings of ALL clocks.* |
| `void MXC_LP_SysRam0Shutdown(void)` | Shutdown System Ram 0 |
| `void MXC_LP_SysRam0PowerUp(void)` | Wakeup System Ram 0 |
| `void MXC_LP_SysRam1Shutdown(void)` | Shutdown System Ram 1 |
| `void MXC_LP_SysRam1PowerUp(void)` | PowerUp System Ram 1 |
| `void MXC_LP_SysRam2Shutdown(void)` | Shutdown System Ram 2 |
| `void MXC_LP_SysRam2PowerUp(void)` | PowerUp System Ram 2 |
| `void MXC_LP_SysRam3Shutdown(void)` | Shutdown System Ram 3 |
| `void MXC_LP_SysRam3PowerUp(void)` | PowerUp System Ram 3 |

## 依赖的其他头文件

- `stdint.h`
- `pwrseq_regs.h`
- `mcr_regs.h`
- `gcr_regs.h`
- `lpcmp.h`
- `gpio.h`
- `tmr.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `lp.h` 自动生成，请勿手改；改脚本后重跑。*
