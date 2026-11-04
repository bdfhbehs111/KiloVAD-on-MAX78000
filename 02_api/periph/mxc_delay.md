# `mxc_delay.h` — 阻塞延时

> **概要**：Asynchronous delay routines based on the SysTick Timer.
> **头文件**：`03_api/headers/mxc_delay.h`
> **驱动实现**：`03_api/source_ai85/SYS/`
> **函数** 5　**宏** 3　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [typedef](#typedef)
- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_delay_complete_t` | `void (*mxc_delay_complete_t)(int result)` |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_DELAY_SEC(s)` | `(((uint32_t)s) * 1000000UL)` |  |
| `MXC_DELAY_MSEC(ms)` | `(ms * 1000UL)` |  |
| `MXC_DELAY_USEC(us)` | `(us)` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_Delay(uint32_t us)` | Blocks and delays for the specified number of microseconds.　*多核分支重复声明，已合并* |
| `int MXC_DelayAsync(uint32_t us, mxc_delay_complete_t callback)` | Starts a non-blocking delay for the specified number of microseconds.　*多核分支重复声明，已合并*　*⚠ MXC_Delay_handler() must be called from the SysTick interrupt service routine or at a rate greater than the SysTick overflow rate.* |
| `int MXC_DelayCheck(void)` | Returns the status of a non-blocking delay request　*多核分支重复声明，已合并* |
| `void MXC_DelayAbort(void)` | Stops an asynchronous delay previously started.　*多核分支重复声明，已合并* |
| `void MXC_DelayHandler(void)` | Processes the delay interrupt. |

## 依赖的其他头文件

- `stdint.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `mxc_delay.h` 自动生成，请勿手改；改脚本后重跑。*
