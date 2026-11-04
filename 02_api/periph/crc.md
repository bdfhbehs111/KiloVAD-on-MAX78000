# `crc.h` — CRC 循环冗余校验

> **概要**：cyclic redundancy check driver.
> **头文件**：`03_api/headers/crc.h`
> **驱动实现**：`03_api/source_ai85/CRC/`
> **函数** 12　**宏** 0　**枚举** 1　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_crc_req_t`

| 字段 | 说明 |
|---|---|
| `uint32_t *dataBuffer` | Pointer to the data |
| `uint32_t dataLen` | Length of the data |
| `uint32_t resultCRC` | Calculated CRC value |

## 枚举类型

### `mxc_crc_bitorder_t`

| 成员 | 说明 |
|---|---|
| `CRC_LSB_FIRST` |  |
| `CRC_MSB_FIRST` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_CRC_Init(void)` | Enable portions of the CRC |
| `int MXC_CRC_Shutdown(void)` | Disable and reset portions of the CRC |
| `void MXC_CRC_Handler(int ch, int error)` | This function should be called from the CRC ISR Handler when using Async functions |
| `void MXC_CRC_SetDirection(mxc_crc_bitorder_t bitOrder)` | Set the bit-order of CRC calculation |
| `mxc_crc_bitorder_t MXC_CRC_GetDirection(void)` | Set the bit-order of CRC calculation |
| `void MXC_CRC_SwapDataIn(mxc_crc_bitorder_t bitOrder)` | Byte Swap CRC Data Input |
| `void MXC_CRC_SwapDataOut(mxc_crc_bitorder_t bitOrder)` | Byte Swap CRC Data output |
| `void MXC_CRC_SetPoly(uint32_t poly)` | Set the Polynomial for CRC calculation |
| `uint32_t MXC_CRC_GetPoly(void)` | Get the polynomial for CRC calculation |
| `uint32_t MXC_CRC_GetResult(void)` | Get the result of a CRC calculation |
| `int MXC_CRC_Compute(mxc_crc_req_t *req)` | Perform a CRC computation　*⚠ The result of the CRC calculation will be placed in the mxc_crc_req_t structure* |
| `int MXC_CRC_ComputeAsync(mxc_crc_req_t *req)` | Perform a CRC computation using DMA　*⚠ The result of the CRC calculation will be placed in the mxc_crc_req_t structure. The user must call MXC_DMA_Handler() in the ISR* |

## 依赖的其他头文件

- `crc_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `crc.h` 自动生成，请勿手改；改脚本后重跑。*
