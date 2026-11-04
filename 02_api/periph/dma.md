# `dma.h` — DMA 直接存储器访问

> **概要**：Direct Memory Access (DMA) driver function prototypes and data types.
> **头文件**：`03_api/headers/dma.h`
> **驱动实现**：`03_api/source_ai85/DMA/`
> **函数** 24　**宏** 0　**枚举** 5　**结构体** 3　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [typedef](#typedef)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_dma_config_t`

| 字段 | 说明 |
|---|---|
| `int ch` | The channel to load the configuration data into |
| `mxc_dma_reqsel_t reqsel` | The request select line to be used (mem2mem, peripheral) |
| `mxc_dma_width_t srcwd` | The source width (could be dependent on FIFO width) |
| `mxc_dma_width_t dstwd` | The destination width (could be dependent on FIFO width) |
| `int srcinc_en` | Whether to increment the source address during the transfer |
| `int dstinc_en` | Whether to increment the source address during the transfer |

### `mxc_dma_srcdst_t`

| 字段 | 说明 |
|---|---|
| `int ch` | The channel to use for the transfer |
| `void *source` | Pointer to the source address, if applicable |
| `void *dest` | Pointer to the destination address, if applicable |
| `int len` | Number of bytes to transfer |

### `mxc_dma_adv_config_t`

| 字段 | 说明 |
|---|---|
| `int ch` | The channel to use for the transfer |
| `mxc_dma_priority_t prio` | The DMA priority for the channel |
| `unsigned int reqwait_en` | Delay the timeout timer start until after first transfer |
| `mxc_dma_timeout_t tosel` | Number of prescaled clocks seen by the channel before a timeout |
| `mxc_dma_prescale_t pssel` | Prescaler for the timeout timer |
| `unsigned int burst_size` | Number of bytes moved in a single burst |

## 枚举类型

### `mxc_dma_priority_t`

| 成员 | 说明 |
|---|---|
| `MXC_DMA_PRIO_HIGH = MXC_V_DMA_CTRL_PRI_HIGH` | High Priority |
| `MXC_DMA_PRIO_MEDHIGH = MXC_V_DMA_CTRL_PRI_MEDHIGH` | Medium High Priority |
| `MXC_DMA_PRIO_MEDLOW = MXC_V_DMA_CTRL_PRI_MEDLOW` | Medium Low Priority |
| `MXC_DMA_PRIO_LOW = MXC_V_DMA_CTRL_PRI_LOW` | Low Priority |

### `mxc_dma_reqsel_t`

| 成员 | 说明 |
|---|---|
| `MXC_DMA_REQUEST_MEMTOMEM = MXC_S_DMA_CTRL_REQUEST_MEMTOMEM` | Memory to Memory DMA Request Selection |
| `MXC_DMA_REQUEST_SPI1RX = MXC_S_DMA_CTRL_REQUEST_SPI1RX` | SPI1 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_SPI0RX = MXC_S_DMA_CTRL_REQUEST_SPI0RX` | SPI0 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_UART0RX = MXC_S_DMA_CTRL_REQUEST_UART0RX` | UART0 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_UART1RX = MXC_S_DMA_CTRL_REQUEST_UART1RX` | UART1 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_I2C0RX = MXC_S_DMA_CTRL_REQUEST_I2C0RX` | I2C0 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_I2C1RX = MXC_S_DMA_CTRL_REQUEST_I2C1RX` | I2C1 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_ADC = MXC_S_DMA_CTRL_REQUEST_ADC` | ADC Receive DMA Request Selection |
| `MXC_DMA_REQUEST_I2C2RX = MXC_S_DMA_CTRL_REQUEST_I2C2RX` | I2C2 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_UART2RX = MXC_S_DMA_CTRL_REQUEST_UART2RX` | UART2 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_AESRX = MXC_S_DMA_CTRL_REQUEST_AESRX` | AES Receive DMA Request Selection |
| `MXC_DMA_REQUEST_UART3RX = MXC_S_DMA_CTRL_REQUEST_UART3RX` | UART3 Receive DMA Request Selection |
| `MXC_DMA_REQUEST_I2SRX = MXC_S_DMA_CTRL_REQUEST_I2SRX` | I2S Receive DMA Request Selection |
| `MXC_DMA_REQUEST_SPI1TX = MXC_S_DMA_CTRL_REQUEST_SPI1TX` | SPI1 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_SPI0TX = MXC_S_DMA_CTRL_REQUEST_SPI0TX` | SPI0 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_UART0TX = MXC_S_DMA_CTRL_REQUEST_UART0TX` | UART0 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_UART1TX = MXC_S_DMA_CTRL_REQUEST_UART1TX` | UART1 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_I2C0TX = MXC_S_DMA_CTRL_REQUEST_I2C0TX` | I2C0 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_I2C1TX = MXC_S_DMA_CTRL_REQUEST_I2C1TX` | I2C1 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_I2C2TX = MXC_S_DMA_CTRL_REQUEST_I2C2TX` | I2C2 Transmit DMA Request Selection */ |
| `MXC_DMA_REQUEST_CRCTX = MXC_S_DMA_CTRL_REQUEST_CRCTX` | CRC Transmit DMA Request Selection */ |
| `MXC_DMA_REQUEST_UART2TX = MXC_S_DMA_CTRL_REQUEST_UART2TX` | UART2 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_AESTX = MXC_S_DMA_CTRL_REQUEST_AESTX` | AES Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_UART3TX = MXC_S_DMA_CTRL_REQUEST_UART3TX` | UART3 Transmit DMA Request Selection |
| `MXC_DMA_REQUEST_I2STX = MXC_S_DMA_CTRL_REQUEST_I2STX` | I2S Transmit DMA Request Selection |

### `mxc_dma_prescale_t`

| 成员 | 说明 |
|---|---|
| `MXC_DMA_PRESCALE_DISABLE = MXC_S_DMA_CTRL_TO_CLKDIV_DIS` | Prescaler disabled |
| `MXC_DMA_PRESCALE_DIV256 = MXC_S_DMA_CTRL_TO_CLKDIV_DIV256` | Divide by 256 |
| `MXC_DMA_PRESCALE_DIV64K = MXC_S_DMA_CTRL_TO_CLKDIV_DIV64K` | Divide by 65,536 |
| `MXC_DMA_PRESCALE_DIV16M = MXC_S_DMA_CTRL_TO_CLKDIV_DIV16M` | Divide by 16,777,216 |

### `mxc_dma_timeout_t`

| 成员 | 说明 |
|---|---|
| `MXC_DMA_TIMEOUT_4_CLK = MXC_S_DMA_CTRL_TO_PER_TO4` | DMA timeout of 4 clocks |
| `MXC_DMA_TIMEOUT_8_CLK = MXC_S_DMA_CTRL_TO_PER_TO8` | DMA timeout of 8 clocks |
| `MXC_DMA_TIMEOUT_16_CLK = MXC_S_DMA_CTRL_TO_PER_TO16` | DMA timeout of 16 clocks |
| `MXC_DMA_TIMEOUT_32_CLK = MXC_S_DMA_CTRL_TO_PER_TO32` | DMA timeout of 32 clocks |
| `MXC_DMA_TIMEOUT_64_CLK = MXC_S_DMA_CTRL_TO_PER_TO64` | DMA timeout of 64 clocks |
| `MXC_DMA_TIMEOUT_128_CLK = MXC_S_DMA_CTRL_TO_PER_TO128` | DMA timeout of 128 clocks |
| `MXC_DMA_TIMEOUT_256_CLK = MXC_S_DMA_CTRL_TO_PER_TO256` | DMA timeout of 256 clocks |
| `MXC_DMA_TIMEOUT_512_CLK = MXC_S_DMA_CTRL_TO_PER_TO512` | DMA timeout of 512 clocks |

### `mxc_dma_width_t`

| 成员 | 说明 |
|---|---|
| `MXC_DMA_WIDTH_BYTE = MXC_V_DMA_CTRL_SRCWD_BYTE` | Using the '_V_' define instead of the '_S_' since these same values will be used to specify the DSTWD also. The API functions will shift the value the correct amount prior to writing the cfg register. DMA transfer in bytes |
| `MXC_DMA_WIDTH_HALFWORD = MXC_V_DMA_CTRL_SRCWD_HALFWORD` | DMA transfer in 16-bit half-words |
| `MXC_DMA_WIDTH_WORD = MXC_V_DMA_CTRL_SRCWD_WORD` | DMA transfer in 32-bit words |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_dma_complete_cb_t` | `void (*mxc_dma_complete_cb_t)(void *dest)` |
| `mxc_dma_trans_chain_t` | `mxc_dma_srcdst_t (*mxc_dma_trans_chain_t)(mxc_dma_srcdst_t dest)` |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_DMA_Init(void)` | Initialize DMA resources　*⚠ On default this function enables DMA peripheral clock. if you wish to manage clock and gpio related things in upper level instead of here. Define MSDK_NO_GPIO_CLK_INIT flag in project.mk file. By this flag this function will remove clock and gpio related codes from file.* |
| `void MXC_DMA_DeInit(void)` | De-Initialize DMA resources. |
| `int MXC_DMA_AcquireChannel(void)` | Request DMA channel |
| `int MXC_DMA_ReleaseChannel(int ch)` | Release DMA channel |
| `int MXC_DMA_ConfigChannel(mxc_dma_config_t config, mxc_dma_srcdst_t srcdst)` | Configure the DMA channel |
| `int MXC_DMA_AdvConfigChannel(mxc_dma_adv_config_t advConfig)` | Configure the DMA channel with more advanced parameters |
| `int MXC_DMA_SetSrcDst(mxc_dma_srcdst_t srcdst)` | Set channel source, destination, and count for the transfer　*⚠ Unless the channel request select is #mxc_dma_srcdst_t = MXC_DMA_REQUEST_MEMTOMEM, either src_addr or dst_addr will be ignored by the DMA engine. In these cases, the address is a don't-care. See the User's Guide for more information.* |
| `int MXC_DMA_GetSrcDst(mxc_dma_srcdst_t *srcdst)` | Get channel source, destination, and count for transfer |
| `int MXC_DMA_SetSrcReload(mxc_dma_srcdst_t srcdstReload)` | Set channel reload source, destination, and count for the transfer　*⚠ Unless the channel request select is #mxc_dma_srcdst_t = MXC_DMA_REQUEST_MEMTOMEM, either src_addr or dst_addr will be ignored by the DMA engine. In these cases, the address is a don't-care. See the User's Guide for more information.* |
| `int MXC_DMA_GetSrcReload(mxc_dma_srcdst_t *srcdstReload)` | Get channel reload source, destination, and count for transfer |
| `int MXC_DMA_SetCallback(int ch, void (*callback)(int, int))` | Set channel interrupt callback |
| `int MXC_DMA_SetChannelInterruptEn(int ch, bool chdis, bool ctz)` | Set channel interrupt　*⚠ Each channel has two interrupts (complete, and count to zero). To enable complete, pass true for chdis. To enable count to zero, pass true for ctz.* |
| `int MXC_DMA_ChannelEnableInt(int ch, int flags)` | Enable channel interrupt　*⚠ Each channel has two interrupts (complete, and count to zero) which must also be enabled with MXC_DMA_SetChannelInterruptEn()* |
| `int MXC_DMA_ChannelDisableInt(int ch, int flags)` | Disable channel interrupt |
| `int MXC_DMA_ChannelGetFlags(int ch)` | Read channel interrupt flags |
| `int MXC_DMA_ChannelClearFlags(int ch, int flags)` | Clear channel interrupt flags |
| `int MXC_DMA_EnableInt(int ch)` | Enable channel interrupt　*⚠ Each channel has two interrupts (complete, and count to zero) which must also be enabled with MXC_DMA_SetChannelInterruptEn()* |
| `int MXC_DMA_DisableInt(int ch)` | Disable channel interrupt |
| `int MXC_DMA_Start(int ch)` | Start transfer |
| `int MXC_DMA_Stop(int ch)` | Stop DMA transfer, irrespective of status (complete or in-progress) |
| `mxc_dma_ch_regs_t *MXC_DMA_GetCHRegs(int ch)` | Get a pointer to the DMA channel registers |
| `void MXC_DMA_Handler(void)` | Interrupt handler function |
| `int MXC_DMA_MemCpy(void *dest, void *src, int len, mxc_dma_complete_cb_t callback)` | Performs a memcpy, using DMA, optionally asynchronous　*⚠ The user must have the DMA interrupt enabled and call MXC_DMA_Handler() from the ISR.* |
| `int MXC_DMA_DoTransfer(mxc_dma_config_t config, mxc_dma_srcdst_t firstSrcDst, mxc_dma_trans_chain_t callback)` | Performs a memcpy, using DMA, optionally asynchronous　*⚠ The user must have the DMA interrupt enabled and call MXC_DMA_Handler() from the ISR.* |

## 依赖的其他头文件

- `stdbool.h`
- `mxc_device.h`
- `dma_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `dma.h` 自动生成，请勿手改；改脚本后重跑。*
