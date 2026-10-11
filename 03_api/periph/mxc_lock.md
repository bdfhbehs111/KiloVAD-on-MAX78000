# `mxc_lock.h` — 自旋锁

> **概要**：Exclusive access lock utility functions.
> **头文件**：`03_api/headers/mxc_lock.h`
> **驱动实现**：`03_api/source_ai85/SYS/`
> **函数** 2　**宏** 0　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_GetLock(uint32_t *lock, uint32_t value)` | Attempts to acquire the lock. |
| `void MXC_FreeLock(uint32_t *lock)` | Free the given lock. |

## 依赖的其他头文件

- `mxc_device.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `mxc_lock.h` 自动生成，请勿手改；改脚本后重跑。*
