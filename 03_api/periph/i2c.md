# `i2c.h` — I2C 总线

> **概要**：Inter-integrated circuit (I2C) communications interface driver.
> **头文件**：`03_api/headers/i2c.h`
> **驱动实现**：`03_api/source_ai85/I2C/`
> **函数** 52　**宏** 4　**枚举** 1　**结构体** 1　**全局变量** 0

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

### `mxc_i2c_req_t`

| 字段 | 说明 |
|---|---|
| `mxc_i2c_regs_t *i2c` | Pointer to I2C registers (selects the I2C block used.) |
| `unsigned int addr` | The 7-bit or 10-bit address of the slave. |
| `unsigned char *tx_buf` | The buffer containing the bytes to write. |
| `unsigned int tx_len` | The number of bytes to write. On return from the function, this will be set to the number of bytes actually transmitted. |
| `unsigned char *rx_buf` | The buffer to read the data into. |
| `unsigned int rx_len` | The number of bytes to read. On return from the function, this will be set to the number of bytes actually received. |
| `int restart` | Controls whether the transaction is terminated with a stop or repeated start condition. Use 0 for a stop, non-zero for repeated start. |
| `mxc_i2c_complete_cb_t callback` | The callback used to indicate the transaction is complete or an error has occurred. This field may be set to NULL if no indication is necessary. This field is only used by the MXC_I2C_MasterTransactionAsync() function. MXC_I2C_MasterTransaction() ignores the callback field. |

## 枚举类型

### `mxc_i2c_slave_event_t`

| 成员 | 说明 |
|---|---|
| `MXC_I2C_EVT_MASTER_WR` | A slave address match occurred with the master requesting a write to the slave. |
| `MXC_I2C_EVT_MASTER_RD` | A slave address match occurred with the master requesting a read from the slave. |
| `MXC_I2C_EVT_RX_THRESH` | The receive FIFO contains more bytes than its threshold level. |
| `MXC_I2C_EVT_TX_THRESH` | The transmit FIFO contains fewer bytes than its threshold level. |
| `MXC_I2C_EVT_TRANS_COMP` | The transaction has ended. |
| `MXC_I2C_EVT_UNDERFLOW` | The master has attempted a read when the transmit FIFO was empty. |
| `MXC_I2C_EVT_OVERFLOW` | The master has written data when the receive FIFO was already full. |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_i2c_getAck_t` | `int (*mxc_i2c_getAck_t)(mxc_i2c_regs_t *i2c, unsigned char byte)` |
| `mxc_i2c_complete_cb_t` | `void (*mxc_i2c_complete_cb_t)(mxc_i2c_req_t *req, int result)` |
| `mxc_i2c_dma_complete_cb_t` | `void (*mxc_i2c_dma_complete_cb_t)(int len, int result)` |
| `mxc_i2c_slave_handler_t` | `int (*mxc_i2c_slave_handler_t)(mxc_i2c_regs_t *i2c, mxc_i2c_slave_event_t event, void *data)` |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_I2C_STD_MODE` | `100000` |  |
| `MXC_I2C_FAST_SPEED` | `400000` |  |
| `MXC_I2C_FASTPLUS_SPEED` | `1000000` |  |
| `MXC_I2C_HIGH_SPEED` | `3400000` |  |

## 函数 API

### Definitions

| 函数原型 | 说明 |
|---|---|
| `int MXC_I2C_Init(mxc_i2c_regs_t *i2c, int masterMode, unsigned int slaveAddr)` | Initialize and enable I2C peripheral. |
| `int MXC_I2C_SetSlaveAddr(mxc_i2c_regs_t *i2c, unsigned int slaveAddr, int idx)` | Set slave address for I2C instances acting as slaves on the bus.　*⚠ Set idx to zero, multiple I2C instances acting as slaves on the bus is not yet supported.* |
| `int MXC_I2C_Shutdown(mxc_i2c_regs_t *i2c)` | Disable and shutdown I2C peripheral. |
| `int MXC_I2C_Reset(mxc_i2c_regs_t *i2c)` | Reset the I2C peripheral.　*⚠ The peripheral will need to be initialized with MXC_I2C_Init() before use* |
| `int MXC_I2C_SetFrequency(mxc_i2c_regs_t *i2c, unsigned int hz)` | Set the frequency of the I2C interface. |
| `int MXC_I2C_GetFrequency(mxc_i2c_regs_t *i2c)` | Get the frequency of the I2C interface. |
| `int MXC_I2C_ReadyForSleep(mxc_i2c_regs_t *i2c)` | Checks if the given I2C bus can be placed in sleep more. This functions checks to see if there are any on-going I2C transactions in progress. If there are transactions in progress, the application should wait until the I2C bus is free before entering a low-power state. |
| `int MXC_I2C_SetClockStretching(mxc_i2c_regs_t *i2c, int enable)` | Enables or disables clock stretching by the slave. Enables or disables clock stretching by the slave. This function has no affect when operating as the master. |
| `int MXC_I2C_GetClockStretching(mxc_i2c_regs_t *i2c)` | Determines if clock stretching has been enabled. |
| `int MXC_I2C_DMA_Init(mxc_i2c_regs_t *i2c, mxc_dma_regs_t *dma, bool use_dma_tx, bool use_dma_rx)` | Initializes the DMA for I2C DMA transactions. This function will release any acquired DMA channels before reacquiring and reconfiguring selected I2C DMA TX or RX channels. |
| `int MXC_I2C_DMA_GetTXChannel(mxc_i2c_regs_t *i2c)` | Retreive the DMA TX Channel associated with I2C instance. |
| `int MXC_I2C_DMA_GetRXChannel(mxc_i2c_regs_t *i2c)` | Retreive the DMA RX Channel associated with I2C instance. |
| `int MXC_I2C_DMA_SetRequestSelect(mxc_i2c_regs_t *i2c, uint8_t *txData, uint8_t *rxData)` | Sets the I2C instance's DMA TX/RX request select. |
| `int MXC_I2C_Start(mxc_i2c_regs_t *i2c)` | Generate a start (or repeated start) condition on the I2C bus. Generate a start (or repeated start) condition on the I2C bus. This function may opt to delay the actual generation of the start condition until data is actually transferred. |
| `int MXC_I2C_Stop(mxc_i2c_regs_t *i2c)` | Generate a stop condition on the I2C bus. |
| `int MXC_I2C_WriteByte(mxc_i2c_regs_t *i2c, unsigned char byte)` | Write a single byte to the I2C bus. Write a single byte to the I2C bus. This function assumes the I2C bus is already in the proper state (i.e. a start condition has already been generated and the bus is in the write phase of an I2C transaction). If any bytes are pending in the FIFO (i.e. in the case of clock stretching), this function will return E_OVERFLOW. |
| `int MXC_I2C_ReadByte(mxc_i2c_regs_t *i2c, unsigned char *byte, int ack)` | Read a single byte from the I2C bus. Read a single byte from the I2C bus. This function assumes the I2C bus is already in the proper state (i.e. a start condition has already been generated and the bus is in the read phase of an I2C transaction). If the FIFO is empty, this function will return E_UNDERFLOW. |
| `int MXC_I2C_ReadByteInteractive(mxc_i2c_regs_t *i2c, unsigned char *byte, mxc_i2c_getAck_t getAck)` | Read a single byte from the I2C bus. Read a single byte from the I2C bus. After the byte is received, the provided callback will be used to determine if the byte should be acknowledged or not before continuing with the rest of the transaction. This function assumes the I2C bus is already in the proper state (i.e. a start condition has already been generated and the bus is in the read phase of an I2C transaction). This function must be called with clock stretching enabled. |
| `int MXC_I2C_Write(mxc_i2c_regs_t *i2c, unsigned char *bytes, unsigned int *len)` | Write multiple bytes to the I2C bus. Write multiple bytes to the I2C bus. This function assumes the I2C bus is already in the proper state (i.e. a start condition has already been generated and the bus is in the write phase of an I2C transaction). |
| `int MXC_I2C_Read(mxc_i2c_regs_t *i2c, unsigned char *bytes, unsigned int *len, int ack)` | Read multiple bytes from the I2C bus. Read multiple byte from the I2C bus. This function assumes the I2C bus is already in the proper state (i.e. a start condition has already been generated and the bus is in the read phase of an I2C transaction). |
| `int MXC_I2C_ReadRXFIFO(mxc_i2c_regs_t *i2c, volatile unsigned char *bytes, unsigned int len)` | Unloads bytes from the receive FIFO. |
| `int MXC_I2C_ReadRXFIFODMA(mxc_i2c_regs_t *i2c, unsigned char *bytes, unsigned int len, mxc_i2c_dma_complete_cb_t callback)` | Unloads bytes from the receive FIFO using DMA for longer reads.　*⚠ The operation is not complete until the callback has been called* |
| `int MXC_I2C_GetRXFIFOAvailable(mxc_i2c_regs_t *i2c)` | Get the number of bytes currently available in the receive FIFO. |
| `int MXC_I2C_WriteTXFIFO(mxc_i2c_regs_t *i2c, volatile unsigned char *bytes, unsigned int len)` | Loads bytes into the transmit FIFO. |
| `int MXC_I2C_WriteTXFIFODMA(mxc_i2c_regs_t *i2c, unsigned char *bytes, unsigned int len, mxc_i2c_dma_complete_cb_t callback)` | Loads bytes into the transmit FIFO using DMA for longer writes.　*⚠ The operation is not complete until the callback has been called* |
| `int MXC_I2C_GetTXFIFOAvailable(mxc_i2c_regs_t *i2c)` | Get the amount of free space available in the transmit FIFO. |
| `void MXC_I2C_ClearRXFIFO(mxc_i2c_regs_t *i2c)` | Removes and discards all bytes currently in the receive FIFO. |
| `void MXC_I2C_ClearTXFIFO(mxc_i2c_regs_t *i2c)` | Removes and discards all bytes currently in the transmit FIFO. |
| `int MXC_I2C_GetFlags(mxc_i2c_regs_t *i2c, unsigned int *flags0, unsigned int *flags1)` | Get the presently set interrupt flags. |
| `void MXC_I2C_ClearFlags(mxc_i2c_regs_t *i2c, unsigned int flags0, unsigned int flags1)` | Clears the Interrupt Flags. |
| `void MXC_I2C_EnableInt(mxc_i2c_regs_t *i2c, unsigned int flags0, unsigned int flags1)` | Enable Interrupts. |
| `void MXC_I2C_DisableInt(mxc_i2c_regs_t *i2c, unsigned int flags0, unsigned int flags1)` | Disable Interrupts. |
| `void MXC_I2C_EnablePreload(mxc_i2c_regs_t *i2c)` | Enables the slave preload mode Use this mode to preload the slave TX FIFO with data that can be sent when the slave is addressed for a read operation without software intervention. |
| `void MXC_I2C_DisablePreload(mxc_i2c_regs_t *i2c)` | Disable the slave preload mode |
| `void MXC_I2C_EnableGeneralCall(mxc_i2c_regs_t *i2c)` | Enables the slave to respond to the general call address |
| `void MXC_I2C_DisableGeneralCall(mxc_i2c_regs_t *i2c)` | Prevents the slave from responding to the general call address |
| `void MXC_I2C_SetTimeout(mxc_i2c_regs_t *i2c, unsigned int timeout)` | Set the I2C Timeout The I2C timeout determines the amount of time the master will wait while the slave is stretching the clock, and the amount of time the slave will stretch the clock while waiting for software to unload the fifo. |
| `unsigned int MXC_I2C_GetTimeout(mxc_i2c_regs_t *i2c)` | Get the current I2C timeout |
| `int MXC_I2C_Recover(mxc_i2c_regs_t *i2c, unsigned int retries)` | Attempts to recover the I2C bus, ensuring the I2C lines are idle. Attempts to recover and reset an I2C bus by sending I2C clocks. During each clock cycle, the SDA line is cycled to determine if the master has control of the line. The following steps are performed to create one SCL clock cycle: 1. Drive SCL low 2. Verify SCL is low 3. Drive SDA low 4. Verify SDA is low 5. Release SDA allowing it to return high 6. Verify SDA is high 7. Release SCL allowing it to return high. 8. Verify SCL is high If any of the steps fail, the bus is considered to still be busy and the sequence is repeated up to the requested number of times. If all steps succeed, a final stop condition is generated on the I2C bus. |
| `int MXC_I2C_MasterTransaction(mxc_i2c_req_t *req)` | Performs a blocking I2C master transaction. Performs a blocking I2C master transaction. These actions will be performed: 1. If necessary, generate a start condition on the bus. 2. Send the slave address with the low bit set to 0 (indicating a write). 3. Transmit req->tx_len bytes of req->tx_buff. 4. Generate a repeated start condition on the bus. 5. Send the slave address with the low bit set to 1 (indicating a read). 6. Receive req->rx_len bytes into req->rx_buf, acknowledging each byte. 7. Generate a stop (or repeated start) condition on the bus. Steps 3-6 will be skipped if req->tx_len and req->rx_len are both 0. Steps 2-4 will be skipped if req->tx_len equals 0. Steps 4-6 will be skipped if req->rx_len equals 0. |
| `int MXC_I2C_MasterTransactionAsync(mxc_i2c_req_t *req)` | Performs a non-blocking I2C master transaction. Performs a non-blocking I2C master transaction. These actions will be performed: 1. If necessary, generate a start condition on the bus. 2. Send the slave address with the low bit set to 0 (indicating a write). 3. Transmit req->tx_len bytes of req->tx_buff. 4. Generate a repeated start condition on the bus. 5. Send the slave address with the low bit set to 1 (indicating a read). 6. Receive req->rx_len bytes into req->rx_buf, acknowledging each byte. 7. Generate a stop (or repeated start) condition on the bus. 8. Execute req->callback to indicate the transaction is complete. Steps 3-6 will be skipped if tx_len and rx_len are both 0. Steps 2-4 will be skipped if tx_len equals 0. Steps 4-6 will be skipped if rx_len equals 0.　*⚠ MXC_I2C_AsyncHandler() must be called periodically for this function to operate properly. Ideally from the I2C ISR.* |
| `int MXC_I2C_MasterTransactionDMA(mxc_i2c_req_t *req)` | Performs a non-blocking I2C Master transaction using DMA for reduced time in the ISR. This function initializes the DMA and acquires DMA channels if MXC_I2C_DMA_Init(...) was not called earlier. It is recommended to initialize the DMA by calling MXC_I2C_DMA_Init(...) function before calling MXC_I2C_MasterTransactionDMA(...). This provides flexibility in setting up generic DMA channel vectors during run-time without knowing what DMA channels will be acquired beforehand. Performs a non-blocking I2C transaction. These actions will be performed: 1. If necessary, generate a start condition on the bus. 2. Send the slave address with the low bit set to 0 (indicating a write). 3. Transmit req->tx_len bytes of req->tx_buff. 4. Generate a repeated start condition on the bus. 5. Send the slave address with the low bit set to 1 (indicating a read). 6. Receive req->rx_len bytes into req->rx_buf, acknowledging each byte. 7. Generate a stop (or repeated start) condition on the bus. 8. Execute req->callback to indicate the transaction is complete. Steps 3-6 will be skipped if tx_len and rx_len are both 0. Steps 2-4 will be skipped if tx_len equals 0. Steps 4-6 will be skipped if rx_len equals 0.　*⚠ MXC_I2C_AsyncHandler() must be called periodically for this function to operate properly. Ideally from the I2C ISR.* |
| `int MXC_I2C_SlaveTransaction(mxc_i2c_regs_t *i2c, mxc_i2c_slave_handler_t callback)` | Performs a blocking I2C slave transaction. Performs a blocking I2C slave transaction. This function will block until a complete transaction with this slave has been performed. A transaction begins with the master addressing the slave and ends with a repeated start condition, a stop condition, or a bus error. The provided callback function will be called for these events: - A slave address match occurs with the master requesting a write to the slave. - A slave address match occurs with the master requesting a read from the slave. - The receive FIFO crosses the set threshold (see MXC_I2C_SetRXThreshold()). The callback code should unload the receive FIFO (see MXC_I2C_ReadFIFO()) to allow the master to send more data. The return value of the callback function will determine if the last byte received should be acknowledged or not. Return 0 to acknowledge, non-zero to not acknowledge. - The transmit FIFO crosses the set threshold (see MXC_I2C_SetTXThreshold()). If the master is expected to read more data from this slave, the callback code should add data to the transmit FIFO (see MXC_I2C_WriteFIFO()). - The transaction ends. If the master was writing to the slave, the receive FIFO may still contain valid data that needs to be retreived (see MXC_I2C_ReadFIFO()). - The transmit FIFO underflows because the master requests data when the transmit FIFO is empty. - The receive FIFO overflows because the master writes data while the receive FIFO was full. If clock stretching is disabled, careful attention must be paid to the timing of the callback to avoid losing data on write or unintentionally nacking a read. |
| `int MXC_I2C_SlaveTransactionAsync(mxc_i2c_regs_t *i2c, mxc_i2c_slave_handler_t callback)` | Performs a non-blocking I2C slave transaction. Performs a non-blocking I2C slave transaction. This request will remain active until a complete transaction with this slave has been performed. A transaction begins with the master begins with the master addressing the slave and ends with a repeated start condition, a stop condition, or a bus error. The provided callback function will be called for these events: - A slave address match occurs with the master requesting a write to the slave. - A slave address match occurs with the master requesting a read from the slave. - The receive FIFO crosses the set threshold (see MXC_I2C_SetRXThreshold()). The callback code should unload the receive FIFO (see MXC_I2C_ReadFIFO()) to allow the master to send more data. The return value of the callback function will determine if the last byte received should be acknowledged or not. Return 0 to acknowledge, non-zero to not acknowledge. - The transmit FIFO crosses the set threshold (see MXC_I2C_SetTXThreshold()). If the master is expected to read more data from this slave, the callback code should add data to the transmit FIFO (see MXC_I2C_WriteFIFO()). - The transaction ends. If the master was writing to the slave, the receive FIFO may still contain valid data that needs to be retreived (see MXC_I2C_ReadFIFO()). - The transmit FIFO underflows because the master requests data when the transmit FIFO is empty. - The receive FIFO overflows because the master writes data while the receive FIFO was full. If clock stretching is disabled, careful attention must be paid to the timing of the callback to avoid losing data on write or unintentionally nacking a read.　*⚠ MXC_I2C_AsyncHandler() must be called peridocally for this function to operate properly.* |
| `int MXC_I2C_SetRXThreshold(mxc_i2c_regs_t *i2c, unsigned int numBytes)` | Set the receive threshold level. When operating as a master, the function sets the receive threshold level for when the master should unload the receive FIFO. Smaller values may consume more CPU cycles, but decrease the chances of the master delaying the generation of I2C bus clocks because it has no room in the FIFO to receive data. Larger values may consume fewer CPU cycles, but risk delays of the I2C clock. When operating as a slave, this function sets the number of bytes the slave transaction functions should receive before issuing a call to their callback function. Smaller values may consume more CPU cycles, but reduce the risk of missing data from the master due to the recieve FIFO being full. Larger values may reduce the number of CPU cycles, but may cause bytes sent from the master to be missed. |
| `int MXC_I2C_GetRXThreshold(mxc_i2c_regs_t *i2c)` | Get the current receive threshold level. |
| `int MXC_I2C_SetTXThreshold(mxc_i2c_regs_t *i2c, unsigned int numBytes)` | Set the transmit threshold level. When operating as a master, the function sets the transmit threshold level for when the master should add additional bytes to the transmit FIFO. Larger values may consume more CPU cycles, but decrease the chances of the master delaying the generation of I2C bus clocks because it has no data in the FIFO to transmit. Smaller values may consume fewer CPU cycles, but risk delays of the I2C clock. When operating as a slave, this function sets the number of bytes the slave transaction functions should transmit before issuing a call to their callback function. Larger values may consume more CPU cycles, but reduce the risk of not having data ready when the master requests it. Smaller values may reduce the number of CPU cycles, but may cause the master to read from an empty FIFO. (The master will read 0xFF in this case.) |
| `int MXC_I2C_GetTXThreshold(mxc_i2c_regs_t *i2c)` | Get the current transmit threshold level. |
| `void MXC_I2C_AsyncStop(mxc_i2c_regs_t *i2c)` | Stop any asynchronous requests in progress. Stop any asynchronous requests in progress. Any callbacks associated with the active transaction will be NOT executed. |
| `void MXC_I2C_AbortAsync(mxc_i2c_regs_t *i2c)` | Abort any asynchronous requests in progress. Abort any asynchronous requests in progress. Any callbacks associated with the active transaction will be executed to indicate when the transaction has been terminated. |
| `void MXC_I2C_AsyncHandler(mxc_i2c_regs_t *i2c)` | The processing function for asynchronous transactions. When using the asynchronous functions, the application must call this function periodically. This can be done from within the I2C interrupt handler or periodically by the application if I2C interrupts are disabled. |
| `void MXC_I2C_DMACallback(int ch, int error)` | The processing function for DMA transactions. When using the DMA functions, the application must call this function periodically. This can be done from within the DMA Interrupt Handler. |

## 依赖的其他头文件

- `stdint.h`
- `stdbool.h`
- `mxc_sys.h`
- `i2c_regs.h`
- `dma_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `i2c.h` 自动生成，请勿手改；改脚本后重跑。*
