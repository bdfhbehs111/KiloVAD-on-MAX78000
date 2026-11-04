# `lpcmp.h` — LPCMP 低功耗比较器

> **概要**：Low Power Comparator(LPCMP) function prototypes and data types.
> **头文件**：`03_api/headers/lpcmp.h`
> **驱动实现**：`03_api/source_ai85/LPCMP/`
> **函数** 7　**宏** 0　**枚举** 2　**结构体** 0　**全局变量** 0

---

## 目录

- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 枚举类型

### `mxc_lpcmp_polarity_t`

| 成员 | 说明 |
|---|---|
| `MXC_LPCMP_POL_RISE = 0` | Comparator interrupt happens on rising edge of comparator output |
| `MXC_LPCMP_POL_FALL = 1` | Comparator interrupt occurs on falling edge of comparator output |

### `mxc_lpcmp_cmpsel_t`

| 成员 | 说明 |
|---|---|
| `MXC_LPCMP_CMP0 = 0` | Comparator output high when positive input is greater than negative input |
| `MXC_LPCMP_CMP1 = 1` | Comparator output high when negative input is greater than positive input |
| `MXC_LPCMP_CMP2 = 2` | Comparator output high when negative input is greater than positive input |
| `MXC_LPCMP_CMP3 = 3` | Comparator output high when negative input is greater than positive input |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_LPCMP_Init(mxc_lpcmp_cmpsel_t cmp)` | enables comparator |
| `int MXC_LPCMP_Shutdown(mxc_lpcmp_cmpsel_t cmp)` | Shutdown comparator |
| `int MXC_LPCMP_EnableInt(mxc_lpcmp_cmpsel_t cmp, mxc_lpcmp_polarity_t pol)` | Enable interrupts |
| `int MXC_LPCMP_DisableInt(mxc_lpcmp_cmpsel_t cmp)` | Disable interrupts |
| `int MXC_LPCMP_GetFlags(mxc_lpcmp_cmpsel_t cmp)` | Returns the interrupt flags set |
| `int MXC_LPCMP_ClearFlags(mxc_lpcmp_cmpsel_t cmp)` | Clear interrupt flags |
| `int MXC_LPCMP_SelectPolarity(mxc_lpcmp_cmpsel_t cmp, mxc_lpcmp_polarity_t pol)` | Select polatity |

## 依赖的其他头文件

- `stdint.h`
- `lpcmp_regs.h`
- `mcr_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `lpcmp.h` 自动生成，请勿手改；改脚本后重跑。*
