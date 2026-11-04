# `trng.h` — TRNG 真随机数发生器

> **概要**：Random number generator driver.
> **头文件**：`03_api/headers/trng.h`
> **驱动实现**：`03_api/source_ai85/TRNG/`
> **函数** 10　**宏** 0　**枚举** 0　**结构体** 0　**全局变量** 0

---

## 目录

- [typedef](#typedef)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## typedef

| 名称 | 原型 |
|---|---|
| `mxc_trng_complete_t` | `void (*mxc_trng_complete_t)(void *req, int result)` |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_TRNG_Init(void)` | Enable portions of the TRNG |
| `void MXC_TRNG_EnableInt(void)` | Enable TRNG Interrupts |
| `void MXC_TRNG_DisableInt(void)` | Disable TRNG Interrupts |
| `int MXC_TRNG_Shutdown(void)` | Disable and reset portions of the TRNG |
| `void MXC_TRNG_Handler(void)` | This function should be called from the TRNG ISR Handler when using Async functions |
| `int MXC_TRNG_RandomInt(void)` | Get a random number |
| `int MXC_TRNG_Random(uint8_t *data, uint32_t len)` | Get a random number of length len |
| `void MXC_TRNG_RandomAsync(uint8_t *data, uint32_t len, mxc_trng_complete_t callback)` | Get a random number of length len, do not block while generating data　*⚠ The user must call MXC_TRNG_Handler() in the ISR* |
| `void MXC_TRNG_GenerateKey(void)` | Generate an AES key and transfer to the AES block |
| `int MXC_TRNG_HealthTest(void)` | Perform health test of the TRNG entropy source |

## 依赖的其他头文件

- `trng_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `trng.h` 自动生成，请勿手改；改脚本后重跑。*
