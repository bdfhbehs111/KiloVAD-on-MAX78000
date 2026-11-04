# `spi.h` — SPI 总线

> **概要**：Serial Peripheral Interface (SPI) communications driver.
> **头文件**：`03_api/headers/spi.h`
> **驱动实现**：`03_api/source_ai85/SPI/`
> **函数** 43　**宏** 0　**枚举** 2　**结构体** 2　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [typedef](#typedef)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_spi_pins_t`

| 字段 | 说明 |
|---|---|
| `bool clock` | Clock pin |
| `bool ss0` | Slave select pin 0 |
| `bool ss1` | Slave select pin 1 |
| `bool ss2` | Slave select pin 2 |
| `bool miso` | miso pin |
| `bool mosi` | mosi pin |
| `bool sdio2` | SDIO2 pin |
| `bool sdio3` | SDIO3 pin |
| `bool vddioh` | VDDIOH Select |

### `mxc_spi_req_t`

| 字段 | 说明 |
|---|---|
| `mxc_spi_regs_t *spi` | Point to SPI registers |
| `int ssIdx` | Slave select line to use (Master only, ignored in slave mode) |
| `int ssDeassert` | 1 - Deassert SS at end of transaction, 0 - leave SS asserted |
| `uint8_t *txData` | Buffer containing transmit data. For character sizes < 8 bits, pad the MSB of each byte with zeros. For character sizes > 8 bits, use two bytes per character and pad the MSB of the upper byte with zeros |
| `uint8_t *rxData` | Buffer to store received data For character sizes < 8 bits, pad the MSB of each byte with zeros. For character sizes > 8 bits, use two bytes per character and pad the MSB of the upper byte with zeros |
| `uint32_t txLen` | Number of bytes to be sent from txData |
| `uint32_t rxLen` | Number of bytes to be stored in rxData |
| `uint32_t txCnt` | Number of bytes actually transmitted from txData |
| `uint32_t rxCnt` | Number of bytes stored in rxData |
| `spi_complete_cb_t completeCB` | Pointer to function called when transaction is complete |

## 枚举类型

### `mxc_spi_width_t`

| 成员 | 说明 |
|---|---|
| `SPI_WIDTH_3WIRE` | 1 Data line, half duplex |
| `SPI_WIDTH_STANDARD` | MISO/MOSI, full duplex |
| `SPI_WIDTH_DUAL` | 2 Data lines, half duplex |
| `SPI_WIDTH_QUAD` | 4 Data lines, half duplex |

### `mxc_spi_mode_t`

| 成员 | 说明 |
|---|---|
| `SPI_MODE_0` | clock phase = 0, clock polarity = 0 |
| `SPI_MODE_1` | clock phase = 0, clock polarity = 1 |
| `SPI_MODE_2` | clock phase = 1, clock polarity = 0 |
| `SPI_MODE_3` | clock phase = 1, clock polarity = 1 |

## typedef

| 名称 | 原型 |
|---|---|
| `spi_complete_cb_t` | `void (*spi_complete_cb_t)(void *req, int result)` |

## 函数 API

### Definitions

| 函数原型 | 说明 |
|---|---|
| `int MXC_SPI_Init(mxc_spi_regs_t *spi, int masterMode, int quadModeUsed, int numSlaves, unsigned ssPolarity, unsigned int hz, mxc_spi_pins_t pins)` | Initialize and enable SPI peripheral. This function initializes everything necessary to call a SPI transaction function. Some parameters are set to defaults as follows: SPI Mode - 0 SPI Width - SPI_WIDTH_STANDARD (even if quadModeUsed is set) These parameters can be modified after initialization using low level functions |
| `int MXC_SPI_InitState(mxc_spi_regs_t *spi)` | Initialize in-memory SPI peripheral state. |
| `int MXC_SPI_Shutdown(mxc_spi_regs_t *spi)` | Disable and shutdown SPI peripheral. |
| `int MXC_SPI_ReadyForSleep(mxc_spi_regs_t *spi)` | Checks if the given SPI bus can be placed in sleep mode. This functions checks to see if there are any on-going SPI transactions in progress. If there are transactions in progress, the application should wait until the SPI bus is free before entering a low-power state. |
| `int MXC_SPI_GetPeripheralClock(mxc_spi_regs_t *spi)` | Returns the frequency of the clock used as the bit rate generator for a given SPI instance. |
| `int MXC_SPI_SetFrequency(mxc_spi_regs_t *spi, unsigned int hz)` | Set the frequency of the SPI interface. This function is applicable in Master mode only |
| `unsigned int MXC_SPI_GetFrequency(mxc_spi_regs_t *spi)` | Get the frequency of the SPI interface. This function is applicable in Master mode only |
| `int MXC_SPI_SetDataSize(mxc_spi_regs_t *spi, int dataSize)` | Sets the number of bits per character |
| `int MXC_SPI_GetDataSize(mxc_spi_regs_t *spi)` | Gets the number of bits per character |
| `int MXC_SPI_SetSlave(mxc_spi_regs_t *spi, int ssIdx)` | Sets the slave select (SS) line used for transmissions This function is applicable in Master mode only |
| `int MXC_SPI_GetSlave(mxc_spi_regs_t *spi)` | Gets the slave select (SS) line used for transmissions This function is applicable in Master mode only |
| `int MXC_SPI_SetWidth(mxc_spi_regs_t *spi, mxc_spi_width_t spiWidth)` | Sets the SPI width used for transmissions |
| `mxc_spi_width_t MXC_SPI_GetWidth(mxc_spi_regs_t *spi)` | Gets the SPI width used for transmissions |
| `int MXC_SPI_SetMode(mxc_spi_regs_t *spi, mxc_spi_mode_t spiMode)` | Sets the spi mode using clock polarity and clock phase |
| `mxc_spi_mode_t MXC_SPI_GetMode(mxc_spi_regs_t *spi)` | Gets the spi mode |
| `int MXC_SPI_StartTransmission(mxc_spi_regs_t *spi)` | Starts a SPI Transmission This function is applicable in Master mode only The user must ensure that there are no ongoing transmissions before calling this function |
| `int MXC_SPI_GetActive(mxc_spi_regs_t *spi)` | Checks the SPI Peripheral for an ongoing transmission This function is applicable in Master mode only |
| `int MXC_SPI_AbortTransmission(mxc_spi_regs_t *spi)` | Aborts an ongoing SPI Transmission This function is applicable in Master mode only |
| `unsigned int MXC_SPI_ReadRXFIFO(mxc_spi_regs_t *spi, unsigned char *bytes, unsigned int len)` | Unloads bytes from the receive FIFO. |
| `unsigned int MXC_SPI_GetRXFIFOAvailable(mxc_spi_regs_t *spi)` | Get the number of bytes currently available in the receive FIFO. |
| `unsigned int MXC_SPI_WriteTXFIFO(mxc_spi_regs_t *spi, unsigned char *bytes, unsigned int len)` | Loads bytes into the transmit FIFO. |
| `unsigned int MXC_SPI_GetTXFIFOAvailable(mxc_spi_regs_t *spi)` | Get the amount of free space available in the transmit FIFO. |
| `void MXC_SPI_ClearRXFIFO(mxc_spi_regs_t *spi)` | Removes and discards all bytes currently in the receive FIFO. |
| `void MXC_SPI_ClearTXFIFO(mxc_spi_regs_t *spi)` | Removes and discards all bytes currently in the transmit FIFO. |
| `int MXC_SPI_SetRXThreshold(mxc_spi_regs_t *spi, unsigned int numBytes)` | Set the receive threshold level. RX FIFO Receive threshold. Smaller values will cause interrupts to occur more often, but reduce the possibility of losing data because of a FIFO overflow. Larger values will reduce the time required by the ISR, but increase the possibility of data loss. Passing an invalid value will cause the driver to use the value already set in the appropriate register. |
| `unsigned int MXC_SPI_GetRXThreshold(mxc_spi_regs_t *spi)` | Get the current receive threshold level. |
| `int MXC_SPI_SetTXThreshold(mxc_spi_regs_t *spi, unsigned int numBytes)` | Set the transmit threshold level. TX FIFO threshold. Smaller values will cause interrupts to occur more often, but reduce the possibility of terminating a transaction early in master mode, or transmitting invalid data in slave mode. Larger values will reduce the time required by the ISR, but increase the possibility errors occurring. Passing an invalid value will cause the driver to use the value already set in the appropriate register. |
| `unsigned int MXC_SPI_GetTXThreshold(mxc_spi_regs_t *spi)` | Get the current transmit threshold level. |
| `unsigned int MXC_SPI_GetFlags(mxc_spi_regs_t *spi)` | Gets the interrupt flags that are currently set These functions should not be used while using non-blocking Transaction Level functions (Async or DMA) |
| `void MXC_SPI_ClearFlags(mxc_spi_regs_t *spi)` | Clears the interrupt flags that are currently set These functions should not be used while using non-blocking Transaction Level functions (Async or DMA) |
| `unsigned int MXC_SPI_GetAndClearFlags(mxc_spi_regs_t *spi)` | Gets and clears the interrupt flags that are currently set These functions should not be used while using non-blocking Transaction Level functions (Async or DMA) |
| `void MXC_SPI_EnableInt(mxc_spi_regs_t *spi, unsigned int intEn)` | Enables specific interrupts These functions should not be used while using non-blocking Transaction Level functions (Async or DMA) |
| `void MXC_SPI_DisableInt(mxc_spi_regs_t *spi, unsigned int intDis)` | Disables specific interrupts These functions should not be used while using non-blocking Transaction Level functions (Async or DMA) |
| `int MXC_SPI_MasterTransaction(mxc_spi_req_t *req)` | Performs a blocking SPI transaction. Performs a blocking SPI transaction. These actions will be performed in Master Mode: 1. Assert the specified SS 2. In Full Duplex Modes, send TX data while receiving RX Data if rxLen > txLen, pad txData with DefaultTXData if txLen > rxLen, discard rxData where rxCnt > rxLen 3. In Half Duplex Modes, send TX Data, then receive RX Data 4. Deassert the specified SS These actions will be performed in Slave Mode: 1. Fill FIFO with txData 2. Wait for SS Assert 3. If needed, pad txData with DefaultTXData 4. Unload RX FIFO as needed 5. On SS Deassert, return |
| `int MXC_SPI_MasterTransactionAsync(mxc_spi_req_t *req)` | Setup an interrupt-driven SPI transaction The TX FIFO will be filled with txData, padded with DefaultTXData if necessary Relevant interrupts will be enabled, and relevant registers set (SS, Width, etc) |
| `int MXC_SPI_MasterTransactionDMA(mxc_spi_req_t *req)` | Setup a DMA driven SPI transaction The TX FIFO will be filled with txData, padded with DefaultTXData if necessary Relevant interrupts will be enabled, and relevant registers set (SS, Width, etc) The lowest-indexed unused DMA channel will be acquired (using the DMA API) and set up to load/unload the FIFOs with as few interrupt-based events as possible. The channel will be reset and returned to the system at the end of the transaction. |
| `int MXC_SPI_SlaveTransaction(mxc_spi_req_t *req)` | Performs a blocking SPI transaction. Performs a blocking SPI transaction. These actions will be performed in Slave Mode: 1. Fill FIFO with txData 2. Wait for SS Assert 3. If needed, pad txData with DefaultTXData 4. Unload RX FIFO as needed 5. On SS Deassert, return |
| `int MXC_SPI_SlaveTransactionAsync(mxc_spi_req_t *req)` | Setup an interrupt-driven SPI transaction The TX FIFO will be filled with txData, padded with DefaultTXData if necessary Relevant interrupts will be enabled, and relevant registers set (SS, Width, etc) |
| `int MXC_SPI_SlaveTransactionDMA(mxc_spi_req_t *req)` | Setup a DMA driven SPI transaction The TX FIFO will be filled with txData, padded with DefaultTXData if necessary Relevant interrupts will be enabled, and relevant registers set (SS, Width, etc) The lowest-indexed unused DMA channel will be acquired (using the DMA API) and set up to load/unload the FIFOs with as few interrupt-based events as possible. The channel will be reset and returned to the system at the end of the transaction. |
| `int MXC_SPI_SetDefaultTXData(mxc_spi_regs_t *spi, unsigned int defaultTXData)` | Sets the TX data to transmit as a 'dummy' byte In single wire master mode, this data is transmitted on MOSI when performing an RX (MISO) only transaction. This defaults to 0. |
| `void MXC_SPI_AbortAsync(mxc_spi_regs_t *spi)` | Abort any asynchronous requests in progress. Abort any asynchronous requests in progress. Any callbacks associated with the active transaction will be executed to indicate when the transaction has been terminated. |
| `void MXC_SPI_AsyncHandler(mxc_spi_regs_t *spi)` | The processing function for asynchronous transactions. When using the asynchronous functions, the application must call this function periodically. This can be done from within the SPI interrupt handler or periodically by the application if SPI interrupts are disabled. |
| `void MXC_SPI_HWSSControl(mxc_spi_regs_t *spi, int state)` | Enable/Disable HW CS control feature. Depending on the application, the user might need to manually drive the slave select pin. The SPI driver automatically drives the SS pin and this function enables/disables this feature. |

## 依赖的其他头文件

- `stdbool.h`
- `spi_regs.h`
- `mxc_sys.h`
- `mxc_assert.h`
- `gpio.h`
- `mxc_pins.h`
- `mxc_lock.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `spi.h` 自动生成，请勿手改；改脚本后重跑。*
