# `gpio.h` — GPIO 通用输入输出

> **概要**：General-Purpose Input/Output (GPIO) function prototypes and data types.
> **头文件**：`03_api/headers/gpio.h`
> **驱动实现**：`03_api/source_ai85/GPIO/`
> **函数** 25　**宏** 36　**枚举** 7　**结构体** 1　**全局变量** 0

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

### `mxc_gpio_cfg_t`

| 字段 | 说明 |
|---|---|
| `mxc_gpio_regs_t *port` | Pointer to GPIO regs |
| `uint32_t mask` | Pin mask (multiple pins may be set) |
| `mxc_gpio_func_t func` | Function type |
| `mxc_gpio_pad_t pad` | Pad type |
| `mxc_gpio_vssel_t vssel` | Voltage select |
| `mxc_gpio_drvstr_t drvstr` | Drive Strength select |

## 枚举类型

### `mxc_gpio_func_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_FUNC_IN` | GPIO Input |
| `MXC_GPIO_FUNC_OUT` | GPIO Output |
| `MXC_GPIO_FUNC_ALT1` | Alternate Function Selection |
| `MXC_GPIO_FUNC_ALT2` | Alternate Function Selection |
| `MXC_GPIO_FUNC_ALT3` | Alternate Function Selection |
| `MXC_GPIO_FUNC_ALT4` | Alternate Function Selection |

### `mxc_gpio_vssel_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_VSSEL_VDDIO` | Set pin to VIDDIO voltage |
| `MXC_GPIO_VSSEL_VDDIOH` | Set pin to VIDDIOH voltage |

### `mxc_gpio_drvstr_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_DRVSTR_0` | Drive Strength GPIO_DS[2][pin]=0b00 |
| `MXC_GPIO_DRVSTR_1` | Drive Strength GPIO_DS[2][pin]=0b01 |
| `MXC_GPIO_DRVSTR_2` | Drive Strength GPIO_DS[2][pin]=0b10 |
| `MXC_GPIO_DRVSTR_3` | Drive Strength GPIO_DS[2][pin]=0b11 |

### `mxc_gpio_pad_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_PAD_NONE` | No pull-up or pull-down |
| `MXC_GPIO_PAD_PULL_UP` | Set pad to strong pull-up |
| `MXC_GPIO_PAD_PULL_DOWN` | Set pad to strong pull-down |
| `MXC_GPIO_PAD_WEAK_PULL_UP` | Set pad to weak pull-up |
| `MXC_GPIO_PAD_WEAK_PULL_DOWN` | Set pad to weak pull-down |

### `mxc_gpio_int_mode_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_INT_LEVEL` | Interrupt is level sensitive Interrupt is edge sensitive |
| `MXC_GPIO_INT_EDGE` |  |

### `mxc_gpio_int_pol_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_INT_FALLING` | Interrupt triggers on falling edge |
| `MXC_GPIO_INT_HIGH` | Interrupt triggers when level is high |
| `MXC_GPIO_INT_RISING` | Interrupt triggers on rising edge |
| `MXC_GPIO_INT_LOW` | Interrupt triggers when level is low Interrupt triggers on either edge |
| `MXC_GPIO_INT_BOTH` |  |

### `mxc_gpio_config_lock_t`

| 成员 | 说明 |
|---|---|
| `MXC_GPIO_CONFIG_UNLOCKED = 0` | Allow changing pins' configuration. |
| `MXC_GPIO_CONFIG_LOCKED` | Ignore changes to a pin's configuration. |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_gpio_callback_fn` | `void (*mxc_gpio_callback_fn)(void *cbdata)` |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_GPIO_PORT_0` | `((uint32_t)(1UL << 0))` |  |
| `MXC_GPIO_PORT_1` | `((uint32_t)(1UL << 1))` |  |
| `MXC_GPIO_PORT_2` | `((uint32_t)(1UL << 2))` |  |
| `MXC_GPIO_PORT_3` | `((uint32_t)(1UL << 3))` |  |
| `MXC_GPIO_PIN_0` | `((uint32_t)(1UL << 0))` |  |
| `MXC_GPIO_PIN_1` | `((uint32_t)(1UL << 1))` |  |
| `MXC_GPIO_PIN_2` | `((uint32_t)(1UL << 2))` |  |
| `MXC_GPIO_PIN_3` | `((uint32_t)(1UL << 3))` |  |
| `MXC_GPIO_PIN_4` | `((uint32_t)(1UL << 4))` |  |
| `MXC_GPIO_PIN_5` | `((uint32_t)(1UL << 5))` |  |
| `MXC_GPIO_PIN_6` | `((uint32_t)(1UL << 6))` |  |
| `MXC_GPIO_PIN_7` | `((uint32_t)(1UL << 7))` |  |
| `MXC_GPIO_PIN_8` | `((uint32_t)(1UL << 8))` |  |
| `MXC_GPIO_PIN_9` | `((uint32_t)(1UL << 9))` |  |
| `MXC_GPIO_PIN_10` | `((uint32_t)(1UL << 10))` |  |
| `MXC_GPIO_PIN_11` | `((uint32_t)(1UL << 11))` |  |
| `MXC_GPIO_PIN_12` | `((uint32_t)(1UL << 12))` |  |
| `MXC_GPIO_PIN_13` | `((uint32_t)(1UL << 13))` |  |
| `MXC_GPIO_PIN_14` | `((uint32_t)(1UL << 14))` |  |
| `MXC_GPIO_PIN_15` | `((uint32_t)(1UL << 15))` |  |
| `MXC_GPIO_PIN_16` | `((uint32_t)(1UL << 16))` |  |
| `MXC_GPIO_PIN_17` | `((uint32_t)(1UL << 17))` |  |
| `MXC_GPIO_PIN_18` | `((uint32_t)(1UL << 18))` |  |
| `MXC_GPIO_PIN_19` | `((uint32_t)(1UL << 19))` |  |
| `MXC_GPIO_PIN_20` | `((uint32_t)(1UL << 20))` |  |
| `MXC_GPIO_PIN_21` | `((uint32_t)(1UL << 21))` |  |
| `MXC_GPIO_PIN_22` | `((uint32_t)(1UL << 22))` |  |
| `MXC_GPIO_PIN_23` | `((uint32_t)(1UL << 23))` |  |
| `MXC_GPIO_PIN_24` | `((uint32_t)(1UL << 24))` |  |
| `MXC_GPIO_PIN_25` | `((uint32_t)(1UL << 25))` |  |
| `MXC_GPIO_PIN_26` | `((uint32_t)(1UL << 26))` |  |
| `MXC_GPIO_PIN_27` | `((uint32_t)(1UL << 27))` |  |
| `MXC_GPIO_PIN_28` | `((uint32_t)(1UL << 28))` |  |
| `MXC_GPIO_PIN_29` | `((uint32_t)(1UL << 29))` |  |
| `MXC_GPIO_PIN_30` | `((uint32_t)(1UL << 30))` |  |
| `MXC_GPIO_PIN_31` | `((uint32_t)(1UL << 31))` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_GPIO_Init(uint32_t portMask)` | Initialize GPIO. |
| `int MXC_GPIO_Shutdown(uint32_t portMask)` | Shutdown GPIO. |
| `int MXC_GPIO_Reset(uint32_t portMask)` | Reset GPIO. |
| `int MXC_GPIO_Config(const mxc_gpio_cfg_t *cfg)` | Configure GPIO pin(s). |
| `int MXC_GPIO_Disable(mxc_gpio_regs_t *port, uint32_t mask)` | Fully disable pin(s), clearing the input buffer, output driver, and pull configuration set by MXC_GPIO_Config(). |
| `uint32_t MXC_GPIO_InGet(mxc_gpio_regs_t *port, uint32_t mask)` | Gets the pin(s) input state. |
| `void MXC_GPIO_OutSet(mxc_gpio_regs_t *port, uint32_t mask)` | Sets the pin(s) to a high level output. |
| `void MXC_GPIO_OutClr(mxc_gpio_regs_t *port, uint32_t mask)` | Clears the pin(s) to a low level output. |
| `uint32_t MXC_GPIO_OutGet(mxc_gpio_regs_t *port, uint32_t mask)` | Gets the pin(s) output state. |
| `void MXC_GPIO_OutPut(mxc_gpio_regs_t *port, uint32_t mask, uint32_t val)` | Write the pin(s) to a desired output level. |
| `void MXC_GPIO_OutToggle(mxc_gpio_regs_t *port, uint32_t mask)` | Toggles the the pin(s) output level. |
| `int MXC_GPIO_IntConfig(const mxc_gpio_cfg_t *cfg, mxc_gpio_int_pol_t pol)` | Configure GPIO interrupt(s) |
| `void MXC_GPIO_EnableInt(mxc_gpio_regs_t *port, uint32_t mask)` | Enables the specified GPIO interrupt |
| `void MXC_GPIO_DisableInt(mxc_gpio_regs_t *port, uint32_t mask)` | Disables the specified GPIO interrupt. |
| `uint32_t MXC_GPIO_GetFlags(mxc_gpio_regs_t *port)` | Gets the interrupt(s) status on a GPIO port |
| `void MXC_GPIO_ClearFlags(mxc_gpio_regs_t *port, uint32_t flags)` | Gets the interrupt(s) status on a GPIO port |
| `void MXC_GPIO_RegisterCallback(const mxc_gpio_cfg_t *cfg, mxc_gpio_callback_fn callback, void *cbdata)` | Registers a callback for the interrupt on a given port and pin. |
| `void MXC_GPIO_Handler(unsigned int port)` | GPIO IRQ Handler. @note If a callback is registered for a given interrupt, the callback function will be called.　*⚠ If a callback is registered for a given interrupt, the callback function will be called.* |
| `int MXC_GPIO_SetVSSEL(mxc_gpio_regs_t *port, mxc_gpio_vssel_t vssel, uint32_t mask)` | Set Voltage select for pins to VDDIO or VDDIOH |
| `void MXC_GPIO_SetWakeEn(mxc_gpio_regs_t *port, uint32_t mask)` | Enables GPIO pins to be used as a wakeup source. |
| `void MXC_GPIO_ClearWakeEn(mxc_gpio_regs_t *port, uint32_t mask)` | Disables GPIO pins from being used as a wakeup source. |
| `uint32_t MXC_GPIO_GetWakeEn(mxc_gpio_regs_t *port)` | Returns the pins currently enabled as wakeup sources. |
| `int MXC_GPIO_SetDriveStrength(mxc_gpio_regs_t *port, mxc_gpio_drvstr_t drvstr, uint32_t mask)` | Set Drive Strength for pins. |
| `void MXC_GPIO_SetConfigLock(mxc_gpio_config_lock_t locked)` | Enables/Disables the lock on all pins' configurations. If locked, any changes to a pin's configuration made through the MXC_GPIO_Config function will be ignored. |
| `mxc_gpio_config_lock_t MXC_GPIO_GetConfigLock(void)` | Reads the current lock state on pin configuration. |

## 依赖的其他头文件

- `gpio_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `gpio.h` 自动生成，请勿手改；改脚本后重跑。*
