# `icc.h` — ICC 双核通信控制器

> **概要**：Instruction Controller Cache(ICC) function prototypes and data types.
> **头文件**：`03_api/headers/icc.h`
> **驱动实现**：`03_api/source_ai85/ICC/`
> **函数** 7　**宏** 0　**枚举** 1　**结构体** 0　**全局变量** 0

---

## 目录

- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 枚举类型

### `mxc_icc_info_t`

| 成员 | 说明 |
|---|---|
| `ICC_INFO_RELNUM` | Identifies the RTL release version |
| `ICC_INFO_PARTNUM` | Specifies the value of C_ID Port Number |
| `ICC_INFO_ID` | Specifies the value of Cache ID |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_ICC_ID(mxc_icc_regs_t *icc, mxc_icc_info_t cid)` | Reads the data from the Cache Id Register. |
| `void MXC_ICC_Enable(mxc_icc_regs_t *icc)` | Enable the instruction cache controller. |
| `void MXC_ICC_Disable(mxc_icc_regs_t *icc)` | Disable the instruction cache controller. |
| `int MXC_ICC_IsEnabled(mxc_icc_regs_t *icc)` | Checks if the instruction cache controller is enabled. |
| `void MXC_ICC_Flush(mxc_icc_regs_t *icc)` | Flush the instruction cache controller. |
| `void MXC_ICC_Invalidate(mxc_icc_regs_t *icc)` | Invalidate the instruction cache controller. |
| `void MXC_ICC_WaitForReady(mxc_icc_regs_t *icc)` | Wait until the instruction cache controller is ready. |

## 依赖的其他头文件

- `stdint.h`
- `icc_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `icc.h` 自动生成，请勿手改；改脚本后重跑。*
