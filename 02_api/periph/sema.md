# `sema.h` — SEMA 硬件信号量

> **概要**：Semaphore (SEMA) function prototypes and data types.
> **头文件**：`03_api/headers/sema.h`
> **驱动实现**：`03_api/source_ai85/SEMA/`
> **函数** 6　**宏** 0　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_SEMA_Init(void)` | Initialize the semaphore peripheral |
| `int MXC_SEMA_GetSema(unsigned sema)` | Attempt to get a semaphore. |
| `int MXC_SEMA_CheckSema(unsigned sema)` | Check a semaphore.　*⚠ Will not be atomic if you call this function and then attempt to MXC_SEMA_GetSema().* |
| `uint32_t MXC_SEMA_Status(void)` | Check all semaphores.　*⚠ Will not be atomic if you call this function and then attempt to MXC_SEMA_GetSema().* |
| `void MXC_SEMA_FreeSema(unsigned sema)` | Frees the semaphore. |
| `int MXC_SEMA_Shutdown(void)` | Shutdown the semaphore peripheral |

## 依赖的其他头文件

- `mxc_device.h`
- `mxc_sys.h`
- `sema_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `sema.h` 自动生成，请勿手改；改脚本后重跑。*
