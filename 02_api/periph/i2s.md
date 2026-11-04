# `i2s.h` — I2S 音频串行接口

> **概要**：I2S (Inter-Integrated Sound) driver function prototypes and data types.
> **头文件**：`03_api/headers/i2s.h`
> **驱动实现**：`03_api/source_ai85/I2S/`
> **函数** 26　**宏** 5　**枚举** 7　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_i2s_req_t`

| 字段 | 说明 |
|---|---|
| `mxc_i2s_ch_mode_t channelMode` |  |
| `mxc_i2s_stereo_t stereoMode` |  |
| `mxc_i2s_wsize_t wordSize` |  |
| `mxc_i2s_justify_t justify` |  |
| `mxc_i2s_bitorder_t bitOrder` |  |
| `mxc_i2s_polarity_t wsPolarity` |  |
| `mxc_i2s_samplesize_t sampleSize` | Optional - Between zero and bitsWord. Consider setting 'adjust' field with this. |
| `uint16_t clkdiv` |  |
| `mxc_i2s_adjust_t adjust` |  |
| `uint8_t bitsWord` | MAX=0x1F. |
| `void *rawData` |  |
| `void *txData` |  |
| `void *rxData` |  |
| `uint32_t length` |  |

## 枚举类型

### `mxc_i2s_stereo_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_STEREO = 0` |  |
| `MXC_I2S_MONO_LEFT_CH = 2` |  |
| `MXC_I2S_MONO_RIGHT_CH = 3` |  |

### `mxc_i2s_polarity_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_POL_NORMAL` |  |
| `MXC_I2S_POL_INVERSE` |  |

### `mxc_i2s_bitorder_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_MSB_FIRST` |  |
| `MXC_I2S_LSB_FIRST` |  |

### `mxc_i2s_justify_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_MSB_JUSTIFY` |  |
| `MXC_I2S_LSB_JUSTIFY` |  |

### `mxc_i2s_wsize_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_WSIZE_BYTE` | Set 8-bit FIFO transactions |
| `MXC_I2S_WSIZE_HALFWORD` | Set 16-bit FIFO transactions |
| `MXC_I2S_WSIZE_WORD` | Set 32-bit FIFO transactions |
| `MXC_I2S_DATASIZE_BYTE = MXC_I2S_WSIZE_BYTE` | Legacy name. Use MXC_I2S_WSIZE_BYTE instead. |
| `MXC_I2S_DATASIZE_HALFWORD = MXC_I2S_WSIZE_HALFWORD` | Legacy name. Use MXC_I2S_WSIZE_HALFWORD instead. |
| `MXC_I2S_DATASIZE_WORD = MXC_I2S_WSIZE_WORD` | Legacy name. Use MXC_I2S_WSIZE_WORD instead. |

### `mxc_i2s_adjust_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_ADJUST_LEFT` |  |
| `MXC_I2S_ADJUST_RIGHT` |  |

### `mxc_i2s_ch_mode_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2S_INTERNAL_SCK_WS_0` |  |
| `MXC_I2S_INTERNAL_SCK_WS_1` |  |
| `MXC_I2S_EXTERNAL_SCK_INTERNAL_WS` |  |
| `MXC_I2S_EXTERNAL_SCK_EXTERNAL_WS` |  |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_I2S_SAMPLESIZE_EIGHT` | `(8)` |  |
| `MXC_I2S_SAMPLESIZE_SIXTEEN` | `(16)` |  |
| `MXC_I2S_SAMPLESIZE_TWENTY` | `(20)` |  |
| `MXC_I2S_SAMPLESIZE_TWENTYFOUR` | `(24)` |  |
| `MXC_I2S_SAMPLESIZE_THIRTYTWO` | `(32)` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_I2S_Init(mxc_i2s_req_t *req)` | Initialize I2S resources |
| `int MXC_I2S_Shutdown(void)` | Release I2S, clear configuration and flush FIFOs |
| `int MXC_I2S_ConfigData(mxc_i2s_req_t *req)` | Configure data to be transmitted based on word and sample size |
| `void MXC_I2S_TXEnable(void)` | Enable TX channel |
| `void MXC_I2S_TXDisable(void)` | Disable TX channel |
| `void MXC_I2S_RXEnable(void)` | Enable RX channel |
| `void MXC_I2S_RXDisable(void)` | Disable RX channel |
| `int MXC_I2S_SetRXThreshold(uint8_t threshold)` | Set threshold for RX FIFO |
| `int MXC_I2S_SetFrequency(mxc_i2s_ch_mode_t mode, uint16_t clkdiv)` | Set I2S Frequency, automatically called by I2S_Init |
| `int MXC_I2S_SetSampleRate(uint32_t smpl_rate, mxc_i2s_wsize_t smpl_sz, uint32_t i2s_clk)` | Sets the clock divider to provide the desired sampling rate. |
| `int MXC_I2S_GetSampleRate(uint32_t i2s_clk)` | Returns the current sampling rate. |
| `int MXC_I2S_CalculateClockDiv(uint32_t smpl_rate, mxc_i2s_wsize_t smpl_sz, uint32_t i2s_clk)` | Calculates the value of the clock divider that should be used in order to get the desired sampling frequency. |
| `void MXC_I2S_Flush(void)` | Flush I2S FIFO |
| `int MXC_I2S_FillTXFIFO(void *txData, mxc_i2s_wsize_t wordSize, int len, int smpl_cnt)` | Fill I2S FIFO with data to transmit |
| `int MXC_I2S_ReadRXFIFO(void *rxData, mxc_i2s_wsize_t wordSize, int len, int smpl_cnt)` | Read audio samples from I2S receive buffer |
| `void MXC_I2S_EnableInt(uint32_t flags)` | Enable Interrupts |
| `void MXC_I2S_DisableInt(uint32_t flags)` | Disable Interrupt |
| `int MXC_I2S_GetFlags(void)` | Get the set interrupt flags |
| `void MXC_I2S_ClearFlags(uint32_t flags)` | Clears Interrupt Flags |
| `int MXC_I2S_Transaction(mxc_i2s_req_t *i2s_req)` | Performs a blocking I2S transaction. |
| `int MXC_I2S_TransactionAsync(mxc_i2s_req_t *i2s_req)` | Sets up an asynchronous I2S transaction. |
| `int MXC_I2S_TXDMAConfig(void *src_addr, int len)` | Configure TX DMA transaction |
| `int MXC_I2S_RXDMAConfig(void *dest_addr, int len)` | Configure RX DMA transaction |
| `void MXC_I2S_Handler(void)` | Handler for asynchronous I2S transactions. |
| `void MXC_I2S_RegisterDMACallback(void (*callback)(int, int))` | Set the callback function pointer for I2S DMA transactions |
| `void MXC_I2S_RegisterAsyncCallback(void (*callback)(int))` | Sets the callback function for asynchronous I2S transactions |

## 依赖的其他头文件

- `mxc_sys.h`
- `dma.h`
- `i2s_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `i2s.h` 自动生成，请勿手改；改脚本后重跑。*
