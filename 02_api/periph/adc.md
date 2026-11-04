# `adc.h` — ADC 逐次逼近模数转换器

> **概要**：Analog to Digital Converter(ADC) function prototypes and data types.
> **头文件**：`03_api/headers/adc.h`
> **驱动实现**：`03_api/source_ai85/ADC/`
> **函数** 32　**宏** 17　**枚举** 5　**结构体** 2　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [typedef](#typedef)
- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_adc_monitor_req_t`

| 字段 | 说明 |
|---|---|
| `mxc_adc_monitor_t monitor` | Monitor to use |
| `mxc_adc_scale_t scale` | Channel scale to use (if external channel) |
| `mxc_adc_chsel_t channel` | Channel to use |
| `int lowThreshold` | Low Threshold for monitor (RAW ADC counts) |
| `int highThreshold` | High Threshold for monitor (RAW ADC counts) |
| `mxc_adc_monitor_cb_t callback` | Function to call when the channel crosses threshold |

### `mxc_adc_conversion_req_t`

| 字段 | 说明 |
|---|---|
| `mxc_adc_chsel_t channel` | Channel to use |
| `mxc_adc_scale_t scale` | Channel scale to use (if external channel) |
| `int rawADCValue` | Result of the conversion |
| `mxc_adc_complete_cb_t callback` | Function to call when callback is complete |

## 枚举类型

### `mxc_adc_chsel_t`

| 成员 | 说明 |
|---|---|
| `MXC_ADC_CH_0 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN0` | Select Channel 0 |
| `MXC_ADC_CH_1 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN1` | Select Channel 1 |
| `MXC_ADC_CH_2 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN2` | Select Channel 2 |
| `MXC_ADC_CH_3 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN3` | Select Channel 3 |
| `MXC_ADC_CH_4 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN4` | Channel 0 divided by 5 |
| `MXC_ADC_CH_5 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN5` | Channel 1 divided by 5 |
| `MXC_ADC_CH_6 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN6` | VDDB divided by 4 |
| `MXC_ADC_CH_7 = MXC_V_ADC_CTRL_ADC_CHSEL_AIN7` | VDD18 input select |
| `MXC_ADC_CH_VCOREA = MXC_V_ADC_CTRL_ADC_CHSEL_VCOREA` | VDD12 input select |
| `MXC_ADC_CH_VCOREB = MXC_V_ADC_CTRL_ADC_CHSEL_VCOREB` |  |
| `MXC_ADC_CH_VRXOUT = MXC_V_ADC_CTRL_ADC_CHSEL_VRXOUT` | VRTC divided by 2 |
| `MXC_ADC_CH_VTXOUT = MXC_V_ADC_CTRL_ADC_CHSEL_VTXOUT` | TMON input select |
| `MXC_ADC_CH_VDDA = MXC_V_ADC_CTRL_ADC_CHSEL_VDDA` |  |
| `MXC_ADC_CH_VDDB = MXC_V_ADC_CTRL_ADC_CHSEL_VDDB` |  |
| `MXC_ADC_CH_VDDIO = MXC_V_ADC_CTRL_ADC_CHSEL_VDDI0` |  |
| `MXC_ADC_CH_VDDIOH = MXC_V_ADC_CTRL_ADC_CHSEL_VDDI0H` |  |
| `MXC_ADC_CH_VREGI = MXC_V_ADC_CTRL_ADC_CHSEL_VREGI` |  |

### `mxc_adc_comp_t`

| 成员 | 说明 |
|---|---|
| `MXC_ADC_COMP_0 = MXC_F_MCR_AINCOMP_AINCOMP0PD` |  |
| `MXC_ADC_COMP_1 = MXC_F_MCR_AINCOMP_AINCOMP1PD` |  |
| `MXC_ADC_COMP_2 = MXC_F_MCR_AINCOMP_AINCOMP2PD` |  |
| `MXC_ADC_COMP_3 = MXC_F_MCR_AINCOMP_AINCOMP3PD` |  |
| `MXC_ADC_COMP_HYST_0 = 1 << MXC_F_MCR_AINCOMP_AINCOMPHYST_POS` | Refer to the V HYST specification in the data sheet electrical characteristics |
| `MXC_ADC_COMP_HYST_1 = 2 << MXC_F_MCR_AINCOMP_AINCOMPHYST_POS` | for the values corresponding to this field value. Refer to the V HYST specification in the data sheet electrical characteristics |

### `mxc_adc_monitor_t`

| 成员 | 说明 |
|---|---|
| `MXC_ADC_MONITOR_0` |  |
| `MXC_ADC_MONITOR_1` |  |
| `MXC_ADC_MONITOR_2` |  |
| `MXC_ADC_MONITOR_3` |  |

### `mxc_adc_scale_t`

| 成员 | 说明 |
|---|---|
| `MXC_ADC_SCALE_2X` | ADC Scale by 2x (this scales ADC Reference by 1/2) |
| `MXC_ADC_SCALE_1` | ADC Scale by 1x (no scaling) |
| `MXC_ADC_SCALE_2` | ADC Scale by 1/2 |
| `MXC_ADC_SCALE_3` | ADC Scale by 1/3 |
| `MXC_ADC_SCALE_4` | ADC Scale by 1/4 |
| `MXC_ADC_SCALE_6` | ADC Scale by 1/6 (this uses 1/3 and an additional 1/2 scaling) |
| `MXC_ADC_SCALE_8` | ADC Scale by 1/8 (this uses 1/4 and an additional 1/2 scaling) |

### `mxc_adc_ref_t`

| 成员 | 说明 |
|---|---|
| `MXC_ADC_REF_INT` | Selects internal bandgap reference |
| `MXC_ADC_REF_EXT` | Selects external reference pins |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_adc_complete_cb_t` | `void (*mxc_adc_complete_cb_t)(void *req, int error)` |
| `mxc_adc_monitor_cb_t` | `void (*mxc_adc_monitor_cb_t)(void *req, int error)` |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN0` | `((uint32_t)(0x00000000UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN1` | `((uint32_t)(0x00000001UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN2` | `((uint32_t)(0x00000002UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN3` | `((uint32_t)(0x00000003UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN4` | `((uint32_t)(0x00000004UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN5` | `((uint32_t)(0x00000005UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN6` | `((uint32_t)(0x00000006UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_AIN7` | `((uint32_t)(0x00000007UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VCOREA` | `((uint32_t)(0x00000008UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VCOREB` | `((uint32_t)(0x00000009UL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VRXOUT` | `((uint32_t)(0x0000000AUL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VTXOUT` | `((uint32_t)(0x0000000BUL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VDDA` | `((uint32_t)(0x0000000CUL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VDDB` | `((uint32_t)(0x0000000DUL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VDDI0` | `((uint32_t)(0x0000000EUL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VDDI0H` | `((uint32_t)(0x0000000FUL))` |  |
| `MXC_V_ADC_CTRL_ADC_CHSEL_VREGI` | `((uint32_t)(0x00000010UL))` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_ADC_Init(void)` | Performs the ADC startup procedure |
| `int MXC_ADC_Shutdown(void)` | Shuts down the ADC |
| `int MXC_ADC_Busy(void)` | Checks if the ADC is busy (performing a conversion) |
| `void MXC_ADC_EnableInt(uint32_t flags)` | Enable specific ADC interrupts |
| `void MXC_ADC_DisableInt(uint32_t flags)` | Disable specific ADC interrupts |
| `int MXC_ADC_GetFlags(void)` | Performs the ADC startup procedure |
| `void MXC_ADC_ClearFlags(uint32_t flags)` | Performs the ADC startup procedure |
| `int MXC_ADC_SetConversionSpeed(uint32_t hz)` | Sets the ADC conversion speed |
| `int MXC_ADC_GetConversionSpeed(void)` | Gets the current ADC conversion speed |
| `void MXC_ADC_SetDataAlignment(int msbJustify)` | Gets the current ADC conversion speed |
| `void MXC_ADC_SetExtScale(mxc_adc_scale_t scale)` | Sets the scaling used for conversions on external channels |
| `void MXC_ADC_RefSelect(mxc_adc_ref_t ref)` | Select the ADC reference source |
| `void MXC_ADC_EnableMonitor(mxc_adc_monitor_t monitors)` | Enable channel high/low monitor　*⚠ This function only enables an already configured monitor* |
| `void MXC_ADC_DisableMonitor(mxc_adc_monitor_t monitors)` | Disable channel high/low monitor　*⚠ This function only disables an already configured monitor* |
| `void MXC_ADC_SetMonitorHighThreshold(mxc_adc_monitor_t monitor, uint32_t threshold)` | Set the high limit for a specific monitor　*⚠ setting a value of 0 disables this limit* |
| `int MXC_ADC_GetMonitorHighThreshold(mxc_adc_monitor_t monitor)` | Set the high limit for a specific monitor |
| `void MXC_ADC_SetMonitorLowThreshold(mxc_adc_monitor_t monitor, uint32_t threshold)` | Set the low limit for a specific monitor　*⚠ setting a value of 0 disables this limit* |
| `int MXC_ADC_GetMonitorLowThreshold(mxc_adc_monitor_t monitor)` | Set the low limit for a specific monitor |
| `void MXC_ADC_SetMonitorChannel(mxc_adc_monitor_t monitor, mxc_adc_chsel_t channel)` | Set a monitor to use a specific channel　*⚠ The monitor must be enabled separately* |
| `int MXC_ADC_GetMonitorChannel(mxc_adc_monitor_t monitor)` | Get the channel used by a monitor |
| `void MXC_ADC_EnableMonitorAsync(mxc_adc_monitor_t monitor, mxc_adc_monitor_cb_t callback)` | Set a callback to be called when a monitor goes out of range　*⚠ The ADC interrupt must be enabled and MXC_ADC_Handler() called in the ISR* |
| `void MXC_ADC_DisableMonitorAsync(mxc_adc_monitor_t monitor)` | Disable a callback for a monitor |
| `int MXC_ADC_StartConversion(mxc_adc_chsel_t channel)` | Perform a conversion on a specific channel　*⚠ The channel must be configured separately* |
| `int MXC_ADC_StartConversionAsync(mxc_adc_chsel_t channel, mxc_adc_complete_cb_t callback)` | Perform a conversion on a specific channel　*⚠ The channel must be configured separately The ADC interrupt must be enabled and MXC_ADC_Handler() called in the ISR places data in the error parameter of the callback function* |
| `int MXC_ADC_Handler(void)` | Call this function from the ADC ISR when using Async API functions |
| `int MXC_ADC_Convert(mxc_adc_conversion_req_t *req)` | Perform a conversion on a specific channel　*⚠ The result will be placed back in the request structure* |
| `int MXC_ADC_ConvertAsync(mxc_adc_conversion_req_t *req)` | Perform a conversion on a specific channel　*⚠ The result will be placed back in the request structure The ADC interrupt must be enabled and MXC_ADC_Handler() called in the ISR* |
| `void MXC_ADC_Monitor(mxc_adc_monitor_req_t req)` | Monitor a specific channel for an out of range event　*⚠ synchronously waits for an out of range event to occur on the monitor* |
| `void MXC_ADC_MonitorAsync(mxc_adc_monitor_req_t req)` | Monitor a specific channel for an out of range event　*⚠ If a callback is included, the ADC interrupt must be enabled and MXC_ADC_Handler() called in the ISR* |
| `void MXC_ADC_EnableComparators(uint32_t mask)` | Enable the Comparators |
| `void MXC_ADC_DisableComparators(uint32_t mask)` | Disable the Comparators |
| `int MXC_ADC_GetData(uint16_t *outdata)` | Gets the result from the previous ADC conversion |

## 依赖的其他头文件

- `stdint.h`
- `adc_regs.h`
- `mcr_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `adc.h` 自动生成，请勿手改；改脚本后重跑。*
