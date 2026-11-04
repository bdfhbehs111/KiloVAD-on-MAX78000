# `cameraif.h` — CameraIF 摄像头并行接口

> **概要**：CAMERAIF function prototypes and data types.
> **头文件**：`03_api/headers/cameraif.h`
> **驱动实现**：`03_api/source_ai85/CAMERAIF/`
> **函数** 9　**宏** 0　**枚举** 4　**结构体** 0　**全局变量** 0

---

## 目录

- [枚举类型](#枚举类型)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 枚举类型

### `mxc_pcif_datawidth_t`

| 成员 | 说明 |
|---|---|
| `MXC_PCIF_DATAWIDTH_8_BIT = 0` |  |
| `MXC_PCIF_DATAWIDTH_10_BIT` |  |
| `MXC_PCIF_DATAWIDTH_12_BIT` |  |

### `mxc_pcif_gpio_datawidth_t`

| 成员 | 说明 |
|---|---|
| `MXC_PCIF_GPIO_DATAWIDTH_8_BIT = 0` |  |
| `MXC_PCIF_GPIO_DATAWIDTH_10_BIT` |  |
| `MXC_PCIF_GPIO_DATAWIDTH_12_BIT` |  |

### `mxc_pcif_readmode_t`

| 成员 | 说明 |
|---|---|
| `MXC_PCIF_READMODE_SINGLE_MODE = 1` |  |
| `MXC_PCIF_READMODE_CONTINUES_MODE` |  |

### `mxc_pcif_timingsel_t`

| 成员 | 说明 |
|---|---|
| `MXC_PCIF_TIMINGSEL_HSYNC_and_VSYNC = 0` |  |
| `MXC_PCIF_TIMINGSEL_SAV_and_EAV` |  |

## 函数 API

### （无章节标注）

| 函数原型 | 说明 |
|---|---|
| `int MXC_PCIF_Init(mxc_pcif_gpio_datawidth_t gpioDataWidth)` | Initialize the Parallel Camera Interface. |
| `void MXC_PCIF_SetDataWidth(mxc_pcif_datawidth_t datawidth)` | Set data width for the camera interface. |
| `void MXC_PCIF_SetTimingSel(mxc_pcif_timingsel_t timingsel)` | Set the desired timing mode for the camera interface. |
| `void MXC_PCIF_SetThreshold(int fifo_thrsh)` | Set camera FIFO threshold. |
| `void MXC_PCIF_EnableInt(uint32_t flags)` | Enable camera interrupts. |
| `void MXC_PCIF_DisableInt(uint32_t flags)` | Disable camera interrupts. |
| `void MXC_PCIF_Start(mxc_pcif_readmode_t readmode)` | Start to capture image from camera interface |
| `void MXC_PCIF_Stop(void)` | Stop capture, disable Parallel camera interface |
| `unsigned int MXC_PCIF_GetData(void)` | Read fifo of PCIF |

## 依赖的其他头文件

- `mxc_device.h`
- `cameraif_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `cameraif.h` 自动生成，请勿手改；改脚本后重跑。*
