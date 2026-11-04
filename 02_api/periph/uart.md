# `uart.h` — UART 串口

> **概要**：Serial Peripheral Interface (UART) communications driver.
> **头文件**：`03_api/headers/uart.h`
> **驱动实现**：`03_api/source_ai85/UART/`
> **函数** 51　**宏** 1　**枚举** 4　**结构体** 1　**全局变量** 0

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

### `mxc_uart_req_t`

| 字段 | 说明 |
|---|---|
| `mxc_uart_regs_t *uart` | Point to UART registers |
| `const uint8_t *txData` | Buffer containing transmit data. For character sizes < 8 bits, pad the MSB of each byte with zeros. For character sizes > 8 bits, use two bytes per character and pad the MSB of the upper byte with zeros |
| `uint8_t *rxData` | Buffer to store received data For character sizes < 8 bits, pad the MSB of each byte with zeros. For character sizes > 8 bits, use two bytes per character and pad the MSB of the upper byte with zeros |
| `uint32_t txLen` | Number of bytes to be sent from txData |
| `uint32_t rxLen` | Number of bytes to be stored in rxData |
| `volatile uint32_t txCnt` | Number of bytes actually transmitted from txData |
| `volatile uint32_t rxCnt` | Number of bytes stored in rxData |
| `mxc_uart_complete_cb_t callback` | Pointer to function called when transaction is complete |

## 枚举类型

### `mxc_uart_stop_t`

| 成员 | 说明 |
|---|---|
| `MXC_UART_STOP_1` | UART Stop 1 clock cycle |
| `MXC_UART_STOP_2` | UART Stop 2 clock cycle (1.5 clocks for 5 bit characters) |

### `mxc_uart_parity_t`

| 成员 | 说明 |
|---|---|
| `MXC_UART_PARITY_DISABLE` | UART Parity Disabled |
| `MXC_UART_PARITY_EVEN_0` | UART Parity Even, 0 based |
| `MXC_UART_PARITY_EVEN_1` | UART Parity Even, 1 based |
| `MXC_UART_PARITY_ODD_0` | UART Parity Odd, 0 based |
| `MXC_UART_PARITY_ODD_1` | UART Parity Odd, 1 based |

### `mxc_uart_flow_t`

| 成员 | 说明 |
|---|---|
| `MXC_UART_FLOW_DIS` | UART Flow Control Disabled |
| `MXC_UART_FLOW_EN` | UART Flow Control Enabled |

### `mxc_uart_clock_t`

| 成员 | 说明 |
|---|---|
| `MXC_UART_APB_CLK = 0` | For UART3 APB clock source is the 8MHz clock |
| `MXC_UART_IBRO_CLK = 2` | IBRO clock can only be used for UART 0, 1 & 2 |
| `MXC_UART_ERTCO_CLK = 4` | ERTCO clock can only be used for UART3 |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_uart_complete_cb_t` | `void (*mxc_uart_complete_cb_t)(mxc_uart_req_t *req, int result)` |
| `mxc_uart_dma_complete_cb_t` | `void (*mxc_uart_dma_complete_cb_t)(mxc_uart_req_t *req, int num, int result)` |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `UART_EXTCLK_FREQ` | `EXTCLK_FREQ` |  |

## 函数 API

### Definitions

| 函数原型 | 说明 |
|---|---|
| `int MXC_UART_Init(mxc_uart_regs_t *uart, unsigned int baud, mxc_uart_clock_t clock)` | Initialize and enable UART peripheral. This function initializes everything necessary to call a UART transaction function. Some parameters are set to defaults as follows: UART Data Size - 8 bits UART Stop Bits - 1 bit UART Parity - None UART Flow Control - None These parameters can be modified after initialization using low level functions |
| `int MXC_UART_Shutdown(mxc_uart_regs_t *uart)` | Disable and shutdown UART peripheral. |
| `int MXC_UART_ReadyForSleep(mxc_uart_regs_t *uart)` | Checks if the given UART bus can be placed in sleep more.　*⚠ This functions checks to see if there are any on-going UART transactions in progress. If there are transactions in progress, the application should wait until the UART bus is free before entering a low-power state.* |
| `int MXC_UART_SetFrequency(mxc_uart_regs_t *uart, unsigned int baud, mxc_uart_clock_t clock)` | Set the frequency of the UART interface. |
| `int MXC_UART_GetFrequency(mxc_uart_regs_t *uart)` | Get the frequency of the UART interface.　*⚠ This function is applicable in Master mode only* |
| `int MXC_UART_SetDataSize(mxc_uart_regs_t *uart, int dataSize)` | Sets the number of bits per character |
| `int MXC_UART_SetStopBits(mxc_uart_regs_t *uart, mxc_uart_stop_t stopBits)` | Sets the number of stop bits sent at the end of a character |
| `int MXC_UART_SetParity(mxc_uart_regs_t *uart, mxc_uart_parity_t parity)` | Sets the type of parity generation used |
| `int MXC_UART_SetFlowCtrl(mxc_uart_regs_t *uart, mxc_uart_flow_t flowCtrl, int rtsThreshold)` | Sets the flow control used |
| `int MXC_UART_SetClockSource(mxc_uart_regs_t *uart, mxc_uart_clock_t clock)` | Sets the clock source for the baud rate generator |
| `mxc_uart_clock_t MXC_UART_GetClockSource(mxc_uart_regs_t *uart)` | Gets the clock source used for the UART instance |
| `int MXC_UART_GetActive(mxc_uart_regs_t *uart)` | Checks the UART Peripheral for an ongoing transmission　*⚠ This function is applicable in Master mode only* |
| `int MXC_UART_AbortTransmission(mxc_uart_regs_t *uart)` | Aborts an ongoing UART Transmission |
| `int MXC_UART_ReadCharacterRaw(mxc_uart_regs_t *uart)` | Reads the next available character. If no character is available, this function will return an error. |
| `int MXC_UART_WriteCharacterRaw(mxc_uart_regs_t *uart, uint8_t character)` | Writes a character on the UART. If the character cannot be written because the transmit FIFO is currently full, this function returns an error. |
| `int MXC_UART_ReadCharacter(mxc_uart_regs_t *uart)` | Reads the next available character |
| `int MXC_UART_WriteCharacter(mxc_uart_regs_t *uart, uint8_t character)` | Writes a character on the UART |
| `int MXC_UART_Read(mxc_uart_regs_t *uart, uint8_t *buffer, int *len)` | Reads the next available character　*⚠ This function blocks until len characters are received See MXC_UART_TransactionAsync() for a non-blocking version* |
| `int MXC_UART_Write(mxc_uart_regs_t *uart, const uint8_t *byte, int *len)` | Writes a byte on the UART |
| `unsigned int MXC_UART_ReadRXFIFO(mxc_uart_regs_t *uart, unsigned char *bytes, unsigned int len)` | Unloads bytes from the receive FIFO. |
| `int MXC_UART_ReadRXFIFODMA(mxc_uart_regs_t *uart, unsigned char *bytes, unsigned int len, mxc_uart_dma_complete_cb_t callback)` | Unloads bytes from the receive FIFO user DMA for longer reads. |
| `unsigned int MXC_UART_GetRXFIFOAvailable(mxc_uart_regs_t *uart)` | Get the number of bytes currently available in the receive FIFO. |
| `unsigned int MXC_UART_WriteTXFIFO(mxc_uart_regs_t *uart, const unsigned char *bytes, unsigned int len)` | Loads bytes into the transmit FIFO. |
| `int MXC_UART_WriteTXFIFODMA(mxc_uart_regs_t *uart, const unsigned char *bytes, unsigned int len, mxc_uart_dma_complete_cb_t callback)` | Loads bytes into the transmit FIFO using DMA for longer writes |
| `unsigned int MXC_UART_GetTXFIFOAvailable(mxc_uart_regs_t *uart)` | Get the amount of free space available in the transmit FIFO. |
| `int MXC_UART_ClearRXFIFO(mxc_uart_regs_t *uart)` | Removes and discards all bytes currently in the receive FIFO. |
| `int MXC_UART_ClearTXFIFO(mxc_uart_regs_t *uart)` | Removes and discards all bytes currently in the transmit FIFO. |
| `int MXC_UART_SetRXThreshold(mxc_uart_regs_t *uart, unsigned int numBytes)` | Set the receive threshold level.　*⚠ RX FIFO Receive threshold. Smaller values will cause interrupts to occur more often, but reduce the possibility of losing data because of a FIFO overflow. Larger values will reduce the time required by the ISR, but increase the possibility of data loss. Passing an invalid value will cause the driver to use the value already set in the appropriate register.* |
| `unsigned int MXC_UART_GetRXThreshold(mxc_uart_regs_t *uart)` | Get the current receive threshold level. |
| `int MXC_UART_SetTXThreshold(mxc_uart_regs_t *uart, unsigned int numBytes)` | Set the transmit threshold level.　*⚠ TX FIFO threshold. Smaller values will cause interrupts to occur more often, but reduce the possibility of terminating a transaction early in master mode, or transmitting invalid data in slave mode. Larger values will reduce the time required by the ISR, but increase the possibility errors occurring. Passing an invalid value will cause the driver to use the value already set in the appropriate register.* |
| `unsigned int MXC_UART_GetTXThreshold(mxc_uart_regs_t *uart)` | Get the current transmit threshold level. |
| `unsigned int MXC_UART_GetFlags(mxc_uart_regs_t *uart)` | Gets the interrupt flags that are currently set　*⚠ These functions should not be used while using non-blocking Transaction Level functions (Async or DMA)* |
| `int MXC_UART_ClearFlags(mxc_uart_regs_t *uart, unsigned int flags)` | Clears the interrupt flags that are currently set　*⚠ These functions should not be used while using non-blocking Transaction Level functions (Async or DMA)* |
| `int MXC_UART_EnableInt(mxc_uart_regs_t *uart, unsigned int mask)` | Enables specific interrupts　*⚠ These functions should not be used while using non-blocking Transaction Level functions (Async or DMA)* |
| `int MXC_UART_DisableInt(mxc_uart_regs_t *uart, unsigned int mask)` | Disables specific interrupts　*⚠ These functions should not be used while using non-blocking Transaction Level functions (Async or DMA)* |
| `unsigned int MXC_UART_GetStatus(mxc_uart_regs_t *uart)` | Gets the status flags that are currently set |
| `int MXC_UART_Transaction(mxc_uart_req_t *req)` | Performs a blocking UART transaction.　*⚠ Performs a blocking UART transaction as follows. If tx_len is non-zero, transmit TX data Once tx_len has been sent, if rx_len is non-zero, receive data* |
| `int MXC_UART_TransactionAsync(mxc_uart_req_t *req)` | Setup an interrupt-driven UART transaction　*⚠ The TX FIFO will be filled with txData if necessary Relevant interrupts will be enabled* |
| `int MXC_UART_TransactionDMA(mxc_uart_req_t *req)` | Setup a DMA driven UART transaction　*⚠ The TX FIFO will be filled with txData if necessary Relevant interrupts will be enabled The DMA channel indicated by the request will be set up to load/unload the FIFOs with as few interrupt-based events as possible. The channel will be reset and returned to the system at the end of the transaction.* |
| `void MXC_UART_DMACallback(int ch, int error)` | The processing function for DMA transactions. When using the DMA functions, the application must call this function periodically. This can be done from within the DMA Interrupt Handler. |
| `int MXC_UART_AsyncCallback(mxc_uart_regs_t *uart, int retVal)` | Async callback |
| `int MXC_UART_AsyncStop(mxc_uart_regs_t *uart)` | stop any async callbacks |
| `int MXC_UART_AbortAsync(mxc_uart_regs_t *uart)` | Abort any asynchronous requests in progress.　*⚠ Abort any asynchronous requests in progress. Any callbacks associated with the active transaction will be executed to indicate when the transaction has been terminated.* |
| `int MXC_UART_AsyncHandler(mxc_uart_regs_t *uart)` | The processing function for asynchronous transactions.　*⚠ When using the asynchronous functions, the application must call this function periodically. This can be done from within the UART interrupt handler or periodically by the application if UART interrupts are disabled.* |
| `uint32_t MXC_UART_GetAsyncTXCount(mxc_uart_req_t *req)` | Provide TXCount for asynchronous transactions.. |
| `uint32_t MXC_UART_GetAsyncRXCount(mxc_uart_req_t *req)` | Provide RXCount for asynchronous transactions.. |
| `int MXC_UART_SetAutoDMAHandlers(mxc_uart_regs_t *uart, bool enable)` | Enable or disable automatic DMA interrupt handlers for the UART module. The @ref MXC_UART_TransactionDMA functions require special interrupt handlers to work. When "Auto" DMA handlers are enabled, the UART drivers will acquire DMA channels and assign the appropriate handlers automatically. The acquired channels are released after each transaction. If "Auto" DMA handlers are disabled, the user must acquire DMA channels manually and assign them to the drivers with the @ref MXC_UART_SetTXDMAChannel and |
| `int MXC_UART_SetTXDMAChannel(mxc_uart_regs_t *uart, unsigned int channel)` | Set the TX (Transmit) DMA channel for a UART module. This function assigns the DMA channel for transmitting data when @ref is MXC_UART_SetAutoDMAHandlers disabled. |
| `int MXC_UART_GetTXDMAChannel(mxc_uart_regs_t *uart)` | Get the TX (Transmit) DMA channel for a UART module. This function retrieves the currently assigned DMA channel for transmitting data when @ref is MXC_UART_SetAutoDMAHandlers disabled. |
| `int MXC_UART_SetRXDMAChannel(mxc_uart_regs_t *uart, unsigned int channel)` | Set the RX (Receive) DMA channel for a UART module. This function assigns the DMA channel for receiving data when @ref is MXC_UART_SetAutoDMAHandlers disabled. |
| `int MXC_UART_GetRXDMAChannel(mxc_uart_regs_t *uart)` | Get the RX (Receive) DMA channel for a UART module. This function retrieves the currently configured DMA channel for receiving data when @ref is MXC_UART_SetAutoDMAHandlers disabled. |

## 依赖的其他头文件

- `stdbool.h`
- `uart_regs.h`
- `mxc_sys.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `uart.h` 自动生成，请勿手改；改脚本后重跑。*
