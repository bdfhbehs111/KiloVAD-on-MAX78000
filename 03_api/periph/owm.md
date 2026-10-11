# `owm.h` — OWM 单总线(1-Wire)主机

> **概要**：Registers, Bit Masks and Bit Positions for the 1-Wire Master
> **头文件**：`03_api/headers/owm.h`
> **驱动实现**：`03_api/source_ai85/OWM/`
> **函数** 34　**宏** 7　**枚举** 1　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_owm_cfg_t`

| 字段 | 说明 |
|---|---|
| `uint8_t int_pu_en` | 1 = internal pullup on. |
| `mxc_owm_ext_pu_t ext_pu_mode` | See #mxc_owm_ext_pu_t. |
| `uint8_t long_line_mode` | 1 = long line mode enable. |

## 枚举类型

### `mxc_owm_ext_pu_t`

| 成员 | 说明 |
|---|---|
| `MXC_OWM_EXT_PU_ACT_HIGH = 0` | Pullup pin is active high when enabled. |
| `MXC_OWM_EXT_PU_ACT_LOW = 1` | Pullup pin is active low when enabled. |
| `MXC_OWM_EXT_PU_UNUSED = 2` | Pullup pin is not used for an external pullup. |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `READ_ROM_COMMAND` | `0x33` |  |
| `MATCH_ROM_COMMAND` | `0x55` |  |
| `SEARCH_ROM_COMMAND` | `0xF0` |  |
| `SKIP_ROM_COMMAND` | `0xCC` |  |
| `OD_SKIP_ROM_COMMAND` | `0x3C` |  |
| `OD_MATCH_ROM_COMMAND` | `0x69` |  |
| `RESUME_COMMAND` | `0xA5` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_OWM_Init(const mxc_owm_cfg_t *cfg)` | Initialize and enable OWM module. |
| `void MXC_OWM_Shutdown(void)` | Shutdown OWM module. |
| `int MXC_OWM_Reset(void)` | Send 1-Wire reset pulse. Will block until transaction is complete. |
| `int MXC_OWM_GetPresenceDetect(void)` | Get the presence pulse detect status. |
| `int MXC_OWM_TouchByte(uint8_t data)` | Send and receive one byte of data. Will block until transaction is complete. |
| `int MXC_OWM_WriteByte(uint8_t data)` | Write one byte of data. Will block until transaction is complete. |
| `int MXC_OWM_ReadByte(void)` | Read one byte of data. Will block until transaction is complete. |
| `int MXC_OWM_TouchBit(uint8_t bit)` | Send and receive one bit of data. Will block until transaction is complete. |
| `int MXC_OWM_WriteBit(uint8_t bit)` | Write one bit of data. Will block until transaction is complete. |
| `int MXC_OWM_ReadBit(void)` | Read one bit of data. Will block until transaction is complete. |
| `int MXC_OWM_Write(uint8_t *data, int len)` | Write multiple bytes of data. Will block until transaction is complete. |
| `int MXC_OWM_Read(uint8_t *data, int len)` | Read multiple bytes of data. Will block until transaction is complete. |
| `int MXC_OWM_ReadROM(uint8_t *ROMCode)` | Starts 1-Wire communication with Read ROM command　*⚠ Only use the Read ROM command with one slave on the bus* |
| `int MXC_OWM_MatchROM(uint8_t *ROMCode)` | Starts 1-Wire communication with Match ROM command |
| `int MXC_OWM_ODMatchROM(uint8_t *ROMCode)` | Starts 1-Wire communication with Overdrive Match ROM command　*⚠ After Overdrive Match ROM command is sent, the OWM is set to overdrive speed. To set back to standard speed use MXC_OWM_SetOverdrive.* |
| `int MXC_OWM_SkipROM(void)` | Starts 1-Wire communication with Skip ROM command |
| `int MXC_OWM_ODSkipROM(void)` | Starts 1-Wire communication with Overdrive Skip ROM command　*⚠ After Overdrive Skip ROM command is sent, the OWM is set to overdrive speed. To set back to standard speed use MXC_OWM_SetOverdrive* |
| `int MXC_OWM_Resume(void)` | Starts 1-Wire communication with Resume command |
| `int MXC_OWM_SearchROM(int newSearch, uint8_t *ROMCode)` | Starts 1-Wire communication with Search ROM command |
| `void MXC_OWM_ClearFlags(uint32_t mask)` | Clear interrupt flags. |
| `unsigned MXC_OWM_GetFlags(void)` | Get interrupt flags. |
| `void MXC_OWM_SetExtPullup(int enable)` | Enables/Disables the External pullup |
| `void MXC_OWM_SetOverdrive(int enable)` | Enables/Disables Overdrive speed |
| `void MXC_OWM_EnableInt(int flags)` | Enables interrupts |
| `void MXC_OWM_DisableInt(int flags)` | Disables interrupts |
| `int MXC_OWM_SetForcePresenceDetect(int enable)` | Enables/Disables driving of OWM_IO low during presence detection |
| `int MXC_OWM_SetInternalPullup(int enable)` | Enables/Disables the Internal pullup |
| `int MXC_OWM_SetExternalPullup(mxc_owm_ext_pu_t ext_pu_mode)` | Enables/Disables the External pullup |
| `int MXC_OWM_SystemClockUpdated(void)` | Call to correct divider if system clock has changed |
| `int MXC_OWM_SetSearchROMAccelerator(int enable)` | Enable/Disable Search ROM Accelerator mode |
| `int MXC_OWM_BitBang_Init(int initialState)` | Prepare OWM for bit bang mode |
| `int MXC_OWM_BitBang_Read(void)` | Read current value of wire |
| `int MXC_OWM_BitBang_Write(int state)` | Set value of wire |
| `int MXC_OWM_BitBang_Disable(void)` | Disable Bit Bang mode |

## 依赖的其他头文件

- `mxc_device.h`
- `mxc_sys.h`
- `owm_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `owm.h` 自动生成，请勿手改；改脚本后重跑。*
