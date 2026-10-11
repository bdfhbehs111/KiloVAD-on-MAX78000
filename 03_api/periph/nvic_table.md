# `nvic_table.h` — NVIC 中断向量表

> **概要**：Interrupt vector table manipulation functions.
> **头文件**：`03_api/headers/nvic_table.h`
> **驱动实现**：`03_api/source_ai85/SYS/`
> **函数** 5　**宏** 0　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `void MXC_NVIC_SetVector(IRQn_Type irqn, void (*irq_callback)(void))` | Set an IRQ hander callback function. If the IRQ table is in flash, this will copy it to RAM and set NVIC to RAM based table. |
| `inline void NVIC_SetVector(IRQn_Type irqn, void (*irq_callback)(void)) { MXC_NVIC_SetVector(irqn, irq_callback)` | 　***已废弃**：Use MXC_NVIC_SetVector instead.  See nvic_table.h for more details.* |
| `void NVIC_SetRAM(void)` | Copy NVIC vector table to RAM and set NVIC to RAM based table. |
| `uint32_t MXC_NVIC_GetVector(IRQn_Type IRQn)` | Get Interrupt Vector |
| `inline void NVIC_GetVector(IRQn_Type irqn) { MXC_NVIC_GetVector(irqn)` | 　***已废弃**：Use MXC_NVIC_GetVector instead.  See nvic_table.h for more details.* |

## 依赖的其他头文件

- `max78000.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `nvic_table.h` 自动生成，请勿手改；改脚本后重跑。*
