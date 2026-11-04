# `mxc_assert.h` — 断言

> **概要**：Assertion checks for debugging.
> **头文件**：`03_api/headers/mxc_assert.h`
> **驱动实现**：`03_api/source_ai85/SYS/`
> **函数** 1　**宏** 4　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [宏定义](#宏定义)
- [函数 API](#函数-api)

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_ASSERT(expr)` | `if (!(expr)) {                                      mxc_a...` |  |
| `MXC_ASSERT_FAIL()` | `mxc_assert("FAIL", __FILE__, __LINE__);` |  |
| `MXC_ASSERT(expr)` | `` |  |
| `MXC_ASSERT_FAIL()` | `` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `void mxc_assert(const char *expr, const char *file, int line)` | Assert an error when the given expression fails during debugging.　*⚠ This is defined as a weak function and can be overridden at the application layer to print the debugging information.* |

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `mxc_assert.h` 自动生成，请勿手改；改脚本后重跑。*
