# `aes.h` — AES 硬件加解密引擎

> **概要**：AES driver.
> **头文件**：`03_api/headers/aes.h`
> **驱动实现**：`03_api/source_ai85/AES/`
> **函数** 23　**宏** 0　**枚举** 2　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [typedef](#typedef)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_aes_req_t`

| 字段 | 说明 |
|---|---|
| `uint32_t length` | Length of the data |
| `uint32_t *inputData` | Pointer to input data |
| `uint32_t *resultData` | Pointer to encrypted data |
| `mxc_aes_keys_t keySize` | Size of AES key |
| `mxc_aes_enc_type_t encryption` | Encrytion type or \ref mxc_aes_enc_type_t |
| `mxc_aes_complete_t callback` | Callback function |

## 枚举类型

### `mxc_aes_keys_t`

| 成员 | 说明 |
|---|---|
| `MXC_AES_128BITS = MXC_S_AES_CTRL_KEY_SIZE_AES128` | Select AES-128 bit key |
| `MXC_AES_192BITS = MXC_S_AES_CTRL_KEY_SIZE_AES192` | Select AES-192 bit key |
| `MXC_AES_256BITS = MXC_S_AES_CTRL_KEY_SIZE_AES256` | Select AES-256 bit key |

### `mxc_aes_enc_type_t`

| 成员 | 说明 |
|---|---|
| `MXC_AES_ENCRYPT_EXT_KEY = 0` | Encryption using External key |
| `MXC_AES_DECRYPT_EXT_KEY = 1` | Encryption using internal key Decryption using internal key |
| `MXC_AES_DECRYPT_INT_KEY = 2` |  |

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_aes_complete_t` | `void (*mxc_aes_complete_t)(void *req, int result)` |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_AES_Init(void)` | Enable portions of the AES |
| `void MXC_AES_EnableInt(uint32_t interrupt)` | Enable AES Interrupts |
| `void MXC_AES_DisableInt(uint32_t interrupt)` | Disable AES Interrupts |
| `int MXC_AES_IsBusy(void)` | Checks the global AES Busy Status |
| `int MXC_AES_Shutdown(void)` | Disable and reset portions of the AES |
| `void MXC_AES_DMACallback(int ch, int error)` | This function should be called from the DMA Handler when using Async functions |
| `void MXC_AES_GenerateKey(void)` | This function should be called before encryption to genrate external key |
| `void MXC_AES_SetKeySize(mxc_aes_keys_t key)` | Set Key size for encryption or decryption |
| `mxc_aes_keys_t MXC_AES_GetKeySize(void)` | Get the currently set key size |
| `void MXC_AES_FlushInputFIFO(void)` | Flush Input Data FIFO |
| `void MXC_AES_FlushOutputFIFO(void)` | Flush Output Data FIFO |
| `void MXC_AES_Start(void)` | Start AES Calculations |
| `uint32_t MXC_AES_GetFlags(void)` | Get Interrupt flags set |
| `void MXC_AES_ClearFlags(uint32_t flags)` | Clear the interrupts |
| `int MXC_AES_Generic(mxc_aes_req_t *req)` | @note The result will be stored in the req structure　*⚠ The result will be stored in the req structure* |
| `int MXC_AES_Encrypt(mxc_aes_req_t *req)` | Perform an encryption　*⚠ The result will be stored in the req structure* |
| `int MXC_AES_Decrypt(mxc_aes_req_t *req)` | Perform a decryption　*⚠ The result will be stored in the req structure* |
| `int MXC_AES_TXDMAConfig(void *src_addr, int len)` | Perform AES TX using DMA. Configures DMA request and starts the transmission. |
| `int MXC_AES_RXDMAConfig(void *dest_addr, int len)` | Perform AES RX using DMA. Configures DMA request and receives data from AES FIFO. |
| `int MXC_AES_GenericAsync(mxc_aes_req_t *req, uint8_t enc)` | Perform encryption or decryption using DMA |
| `int MXC_AES_EncryptAsync(mxc_aes_req_t *req)` | Perform an encryption using Interrupt　*⚠ The result will be stored in the req structure. The user needs to call MXC_AES_Handler() in the ISR* |
| `int MXC_AES_DecryptAsync(mxc_aes_req_t *req)` | Perform a decryption using Interrupt　*⚠ The result will be stored in the req structure. The user needs to call MXC_AES_Handler() in the ISR* |
| `void MXC_AES_SetExtKey(const void *key, mxc_aes_keys_t len)` | Set the external key |

## 依赖的其他头文件

- `aes_regs.h`
- `aeskeys_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `aes.h` 自动生成，请勿手改；改脚本后重跑。*
