# `pt.h` — PT 脉冲序列发生器

> **概要**：Pulse Train data types, definitions and function prototypes.
> **头文件**：`03_api/headers/pt.h`
> **驱动实现**：`03_api/source_ai85/PT/`
> **函数** 15　**宏** 0　**枚举** 1　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_pt_cfg_t`

| 字段 | 说明 |
|---|---|
| `unsigned channel` | PT Channel to use |
| `uint32_t bps` | pulse train bit rate |
| `uint32_t pattern` | Output pattern to shift out, starts at LSB |
| `uint8_t ptLength` | Number of bits in pulse train, 0 = 32bits, 1 = non valid , 2 = 2 bits, ... |
| `uint16_t loop` | Number of times to repeat the train, 0 = continuous |
| `uint16_t loopDelay` | Delay between loops specified in bits Example: loopDelay = 4, delays time = time it takes to shift out 4 bits |

## 枚举类型

### `mxc_clk_scale_t`

| 成员 | 说明 |
|---|---|
| `MXC_PT_CLK_DIV1` |  |
| `MXC_PT_CLK_DIV2` |  |
| `MXC_PT_CLK_DIV4` |  |
| `MXC_PT_CLK_DIV8` |  |
| `MXC_PT_CLK_DIV16` |  |
| `MXC_PT_CLK_DIV32` |  |
| `MXC_PT_CLK_DIV64` |  |
| `MXC_PT_CLK_DIV128` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `void MXC_PT_Init(mxc_clk_scale_t clk_scale)` | This function initializes the pulse trains to a known stopped state and sets the global PT clock scale.　*⚠ If you wish to manage clock settings externally, define the flag MSDK_NO_GPIO_CLK_INIT.* |
| `void MXC_PT_Shutdown(uint32_t pts)` | Shutdown the pulse train channel/channels.　*⚠ Shutdown pulse train channel/channels and delete config.* |
| `int MXC_PT_Config(mxc_pt_cfg_t *cfg)` | Configures the pulse train in the specified mode.　*⚠ The pulse train cannot be running when this function is called.* |
| `int MXC_PT_SqrWaveConfig(unsigned channel, uint32_t freq)` | Configures the pulse train in the square wave mode.　*⚠ The pulse train cannot be running when this function is called* |
| `void MXC_PT_Start(unsigned pts)` | Starts the pulse trains specified. |
| `void MXC_PT_Stop(unsigned pts)` | Stops pulse trains. |
| `uint32_t MXC_PT_IsActive(uint32_t pts)` | Determines if the pulse trains selected are running |
| `void MXC_PT_SetPattern(unsigned pts, uint32_t pattern)` | Sets the pattern of the pulse train |
| `void MXC_PT_EnableInt(uint32_t pts)` | Enable interrupts for the pulse trains selected. |
| `void MXC_PT_DisableInt(uint32_t pts)` | Disable interrupts for the pulse trains selected. |
| `uint32_t MXC_PT_GetFlags(void)` | Gets the pulse trains's interrupt flags. |
| `void MXC_PT_ClearFlags(uint32_t flags)` | Clears the pulse train's interrupt flag. |
| `void MXC_PT_EnableRestart(unsigned start, unsigned stop, uint8_t restartIndex)` | Setup and enables a pulse train to restart after another pulse train has exited its loop. Each pulse train can have up to two restart triggers. |
| `void MXC_PT_DisableRestart(unsigned channel, uint8_t restartIndex)` | Disable the restart for the specified pulse train |
| `void MXC_PT_Resync(uint32_t pts)` | Resynchronize individual pulse trains together. Resync will stop those resync_pts; others will be still running |

## 依赖的其他头文件

- `stdio.h`
- `pt.h`
- `gcr_regs.h`
- `pt_regs.h`
- `ptg_regs.h`
- `mxc_device.h`
- `mxc_errors.h`
- `mxc_assert.h`
- `mxc_sys.h`
- `mcr_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `pt.h` 自动生成，请勿手改；改脚本后重跑。*
