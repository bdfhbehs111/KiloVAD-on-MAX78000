# `flc.h` — FLC 闪存控制器

> **概要**：Flash Controller driver.
> **头文件**：`03_api/headers/flc.h`
> **驱动实现**：`03_api/source_ai85/FLC/`
> **函数** 16　**宏** 2　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_FLASH_PAGE_MASK` | `~(MXC_FLASH_PAGE_SIZE - 1)` |  |
| `MXC_FLASH_PAGE_ADDR(page)` | `(MXC_FLASH_MEM_BASE + ((uint32_t)page * MXC_FLASH_PAGE_SI...` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_FLC_Init(void)` | Initializes the Flash Controller for erase/write operations |
| `int MXC_FLC_Busy(void)` | Checks if Flash Controller is busy. |
| `int MXC_FLC_MassErase(void)` | Erases the entire flash array.　*⚠ This function must be executed from RAM.* |
| `int MXC_FLC_PageErase(uint32_t address)` | Erases the page of flash at the specified address.　*⚠ This function must be executed from RAM.* |
| `void MXC_FLC_Read(int address, void *buffer, int len)` | Read bytes from a flash address. |
| `int MXC_FLC_Write(uint32_t address, uint32_t length, uint32_t *buffer)` | Writes data to flash.　*⚠ This function must be executed from RAM.* |
| `int MXC_FLC_Write32(uint32_t address, uint32_t data)` | Writes 32 bits of data to flash.　*⚠ This function must be executed from RAM.* |
| `int MXC_FLC_Write128(uint32_t address, uint32_t *data)` | Writes 128 bits of data to flash.　*⚠ This function must be executed from RAM.* |
| `int MXC_FLC_EnableInt(uint32_t flags)` | Enable flash interrupts |
| `int MXC_FLC_DisableInt(uint32_t flags)` | Disable flash interrupts |
| `int MXC_FLC_GetFlags(void)` | Retrieve flash interrupt flags |
| `int MXC_FLC_ClearFlags(uint32_t flags)` | Clear flash interrupt flags　*⚠ Provide the bit position to clear, even if the flag is write-0-to-clear* |
| `int MXC_FLC_UnlockInfoBlock(uint32_t address)` | Unlock info block |
| `int MXC_FLC_LockInfoBlock(uint32_t address)` | Lock info block |
| `int MXC_FLC_BlockPageWrite(uint32_t address)` | Blocks write operations to the flash page associated with the 'address' argument　*⚠ Flash pages cannot be unblocked except for on POR and external resets* |
| `int MXC_FLC_BlockPageRead(uint32_t address)` | Blocks read operations from the flash page associated with the 'address' argument　*⚠ Flash pages cannot be unblocked except for on POR and external resets* |

## 依赖的其他头文件

- `flc_regs.h`
- `mxc_sys.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `flc.h` 自动生成，请勿手改；改脚本后重跑。*
