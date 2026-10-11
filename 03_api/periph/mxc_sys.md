# `mxc_sys.h` — 系统时钟/复位/外设使能

> **概要**：System level header file.
> **头文件**：`03_api/headers/mxc_sys.h`
> **驱动实现**：`03_api/source_ai85/SYS/`
> **函数** 21　**宏** 4　**枚举** 4　**结构体** 1　**全局变量** 0

---

## 目录

- [结构体](#结构体)
- [枚举类型](#枚举类型)
- [宏定义](#宏定义)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 结构体

> 调 API 前要先填这些结构体，字段名必须完全一致。

### `mxc_crit_state_t`

| 字段 | 说明 |
|---|---|
| `int ie_status` |  |
| `int in_critical` |  |

## 枚举类型

### `mxc_sys_reset_t`

| 成员 | 说明 |
|---|---|
| `MXC_SYS_RESET0_DMA = MXC_F_GCR_RST0_DMA_POS` | Reset DMA |
| `MXC_SYS_RESET0_WDT0 = MXC_F_GCR_RST0_WDT0_POS` | Reset WDT |
| `MXC_SYS_RESET0_GPIO0 = MXC_F_GCR_RST0_GPIO0_POS` | Reset GPIO0 |
| `MXC_SYS_RESET0_GPIO1 = MXC_F_GCR_RST0_GPIO1_POS` | Reset GPIO1 |
| `MXC_SYS_RESET0_TMR0 = MXC_F_GCR_RST0_TMR0_POS` | Reset TMR0 |
| `MXC_SYS_RESET0_TMR1 = MXC_F_GCR_RST0_TMR1_POS` | Reset TMR1 |
| `MXC_SYS_RESET0_TMR2 = MXC_F_GCR_RST0_TMR2_POS` | Reset TMR2 |
| `MXC_SYS_RESET0_TMR3 = MXC_F_GCR_RST0_TMR3_POS` | Reset TMR3 |
| `MXC_SYS_RESET0_UART0 = MXC_F_GCR_RST0_UART0_POS` | Reset UART0 |
| `MXC_SYS_RESET0_UART1 = MXC_F_GCR_RST0_UART1_POS` | Reset UART1 |
| `MXC_SYS_RESET0_SPI1 = MXC_F_GCR_RST0_SPI1_POS` | Reset SPI1 |
| `MXC_SYS_RESET0_I2C0 = MXC_F_GCR_RST0_I2C0_POS` | Reset I2C0 |
| `MXC_SYS_RESET0_RTC = MXC_F_GCR_RST0_RTC_POS` | Reset RTC |
| `MXC_SYS_RESET0_SMPHR = MXC_F_GCR_RST0_SMPHR_POS` | Reset SMPHR |
| `MXC_SYS_RESET0_TRNG = MXC_F_GCR_RST0_TRNG_POS` | Reset TRNG |
| `MXC_SYS_RESET0_CNN = MXC_F_GCR_RST0_CNN_POS` | Reset CNN |
| `MXC_SYS_RESET0_ADC = MXC_F_GCR_RST0_ADC_POS` | Reset ADC |
| `MXC_SYS_RESET0_UART2 = MXC_F_GCR_RST0_UART2_POS` | Reset UART2 |
| `MXC_SYS_RESET0_SOFT = MXC_F_GCR_RST0_SOFT_POS` | Soft reset |
| `MXC_SYS_RESET0_PERIPH = MXC_F_GCR_RST0_PERIPH_POS` | Peripheral reset |
| `MXC_SYS_RESET0_SYS = MXC_F_GCR_RST0_SYS_POS` | System reset |
| `MXC_SYS_RESET1_I2C1 = (MXC_F_GCR_RST1_I2C1_POS + 32)` | RESET1 Below this line we add 32 to separate RESET0 and RESET1 Reset I2C1 |
| `MXC_SYS_RESET1_PT = (MXC_F_GCR_RST1_PT_POS + 32)` | Reset PT |
| `MXC_SYS_RESET1_OWM = (MXC_F_GCR_RST1_OWM_POS + 32)` | Reset OWM |
| `MXC_SYS_RESET1_CRC = (MXC_F_GCR_RST1_CRC_POS + 32)` | Reset CRC |
| `MXC_SYS_RESET1_AES = (MXC_F_GCR_RST1_AES_POS + 32)` | Reset AES |
| `MXC_SYS_RESET1_SMPHR = (MXC_F_GCR_RST1_SMPHR_POS + 32)` | Reset SMPHR |
| `MXC_SYS_RESET1_I2C2 = (MXC_F_GCR_RST1_I2C2_POS + 32)` | Reset I2C2 |
| `MXC_SYS_RESET1_I2S = (MXC_F_GCR_RST1_I2S_POS + 32)` | Reset I2S |
| `MXC_SYS_RESET1_DVS = (MXC_F_GCR_RST1_DVS_POS + 32)` | Reset DVS |
| `MXC_SYS_RESET1_SIMO = (MXC_F_GCR_RST1_SIMO_POS + 32)` | Reset SIMO |
| `MXC_SYS_RESET1_SPI0 = (MXC_F_GCR_RST1_SPI0_POS + 32)` | Reset SPI0 |
| `MXC_SYS_RESET1_CPU1 = (MXC_F_GCR_RST1_CPU1_POS + 32)` | Reset CPU1 |
| `MXC_SYS_RESET_GPIO2 = (MXC_F_LPGCR_RST_GPIO2_POS + 64)` | LPGCR RESET Below this line we add 64 to separate LPGCR and GCR Reset GPIO2 |
| `MXC_SYS_RESET_WDT1 = (MXC_F_LPGCR_RST_WDT1_POS + 64)` | Reset WDT1 |
| `MXC_SYS_RESET_TMR4 = (MXC_F_LPGCR_RST_TMR4_POS + 64)` | Reset TMR4 |
| `MXC_SYS_RESET_TMR5 = (MXC_F_LPGCR_RST_TMR5_POS + 64)` | Reset TMR5 |
| `MXC_SYS_RESET_UART3 = (MXC_F_LPGCR_RST_UART3_POS + 64)` | Reset UART3 |
| `MXC_SYS_RESET_LPCOMP = (MXC_F_LPGCR_RST_LPCOMP_POS + 64)` | Reset LPCOMP |

### `mxc_sys_periph_clock_t`

| 成员 | 说明 |
|---|---|
| `MXC_SYS_PERIPH_CLOCK_GPIO0 = MXC_F_GCR_PCLKDIS0_GPIO0_POS` | Disable MXC_F_GCR_PCLKDIS0_GPIO0 clock |
| `MXC_SYS_PERIPH_CLOCK_GPIO1 = MXC_F_GCR_PCLKDIS0_GPIO1_POS` | Disable MXC_F_GCR_PCLKDIS0_GPIO1 clock |
| `MXC_SYS_PERIPH_CLOCK_DMA = MXC_F_GCR_PCLKDIS0_DMA_POS` | Disable MXC_F_GCR_PCLKDIS0_DMA clock |
| `MXC_SYS_PERIPH_CLOCK_SPI1 = MXC_F_GCR_PCLKDIS0_SPI1_POS` | Disable MXC_F_GCR_PCLKDIS0_SPI1 clock |
| `MXC_SYS_PERIPH_CLOCK_UART0 = MXC_F_GCR_PCLKDIS0_UART0_POS` | Disable MXC_F_GCR_PCLKDIS0_UART0 clock |
| `MXC_SYS_PERIPH_CLOCK_UART1 = MXC_F_GCR_PCLKDIS0_UART1_POS` | Disable MXC_F_GCR_PCLKDIS0_UART1 clock |
| `MXC_SYS_PERIPH_CLOCK_I2C0 = MXC_F_GCR_PCLKDIS0_I2C0_POS` | Disable MXC_F_GCR_PCLKDIS0_I2C0 clock |
| `MXC_SYS_PERIPH_CLOCK_TMR0 = MXC_F_GCR_PCLKDIS0_TMR0_POS` | Disable MXC_F_GCR_PCLKDIS0_TMR0 clock |
| `MXC_SYS_PERIPH_CLOCK_TMR1 = MXC_F_GCR_PCLKDIS0_TMR1_POS` | Disable MXC_F_GCR_PCLKDIS0_TMR1 clock |
| `MXC_SYS_PERIPH_CLOCK_TMR2 = MXC_F_GCR_PCLKDIS0_TMR2_POS` | Disable MXC_F_GCR_PCLKDIS0_TMR2 clock |
| `MXC_SYS_PERIPH_CLOCK_TMR3 = MXC_F_GCR_PCLKDIS0_TMR3_POS` | Disable MXC_F_GCR_PCLKDIS0_T3 clock |
| `MXC_SYS_PERIPH_CLOCK_ADC = MXC_F_GCR_PCLKDIS0_ADC_POS` | Disable MXC_F_GCR_PCLKDIS0_ADC clock |
| `MXC_SYS_PERIPH_CLOCK_CNN = MXC_F_GCR_PCLKDIS0_CNN_POS` | Disable MXC_F_GCR_PCLKDIS0_CNN clock |
| `MXC_SYS_PERIPH_CLOCK_I2C1 = MXC_F_GCR_PCLKDIS0_I2C1_POS` | Disable MXC_F_GCR_PCLKDIS0_I2C1 clock |
| `MXC_SYS_PERIPH_CLOCK_PT = MXC_F_GCR_PCLKDIS0_PT_POS` | Disable MXC_F_GCR_PCLKDIS0_PT clock |
| `MXC_SYS_PERIPH_CLOCK_UART2 = (MXC_F_GCR_PCLKDIS1_UART2_POS + 32)` | PCLKDIS1 Below this line we add 32 to separate PCLKDIS0 and PCLKDIS1 Disable MXC_F_GCR_PCLKDIS1_UART2 clock |
| `MXC_SYS_PERIPH_CLOCK_TRNG = (MXC_F_GCR_PCLKDIS1_TRNG_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_TRNG clock |
| `MXC_SYS_PERIPH_CLOCK_SMPHR = (MXC_F_GCR_PCLKDIS1_SMPHR_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_SMPHR clock |
| `MXC_SYS_PERIPH_CLOCK_OWIRE = (MXC_F_GCR_PCLKDIS1_OWM_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_OWM clock |
| `MXC_SYS_PERIPH_CLOCK_CRC = (MXC_F_GCR_PCLKDIS1_CRC_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_CRC clock |
| `MXC_SYS_PERIPH_CLOCK_AES = (MXC_F_GCR_PCLKDIS1_AES_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_AES clock |
| `MXC_SYS_PERIPH_CLOCK_I2S = (MXC_F_GCR_PCLKDIS1_I2S_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_I2S clock |
| `MXC_SYS_PERIPH_CLOCK_SPI0 = (MXC_F_GCR_PCLKDIS1_SPI0_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_SPI0 clock |
| `MXC_SYS_PERIPH_CLOCK_PCIF = (MXC_F_GCR_PCLKDIS1_PCIF_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_PCIF clock |
| `MXC_SYS_PERIPH_CLOCK_I2C2 = (MXC_F_GCR_PCLKDIS1_I2C2_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_I2C2 clock |
| `MXC_SYS_PERIPH_CLOCK_WDT0 = (MXC_F_GCR_PCLKDIS1_WDT0_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_WDT0 clock |
| `MXC_SYS_PERIPH_CLOCK_CPU1 = (MXC_F_GCR_PCLKDIS1_CPU1_POS + 32)` | Disable MXC_F_GCR_PCLKDIS1_CPU1 clock |
| `MXC_SYS_PERIPH_CLOCK_GPIO2 = (MXC_F_LPGCR_PCLKDIS_GPIO2_POS + 64)` | LPGCR PCLKDIS Below this line we add 64 to seperate GCR and LPGCR registers Disable MXC_F_LPGCR_PCLKDIS_GPIO2 clock |
| `MXC_SYS_PERIPH_CLOCK_WDT1 = (MXC_F_LPGCR_PCLKDIS_WDT1_POS + 64)` | Disable MXC_F_LPGCR_PCLKDIS_WDT2 clock |
| `MXC_SYS_PERIPH_CLOCK_TMR4 = (MXC_F_LPGCR_PCLKDIS_TMR4_POS + 64)` | Disable MXC_F_LPGCR_PCLKDIS_TMR4 clock |
| `MXC_SYS_PERIPH_CLOCK_TMR5 = (MXC_F_LPGCR_PCLKDIS_TMR5_POS + 64)` | Disable MXC_F_LPGCR_PCLKDIS_TMR5 clock |
| `MXC_SYS_PERIPH_CLOCK_UART3 = (MXC_F_LPGCR_PCLKDIS_UART3_POS + 64)` | Disable MXC_F_LPGCR_PCLKDIS_UART3 clock |
| `MXC_SYS_PERIPH_CLOCK_LPCOMP = (MXC_F_LPGCR_PCLKDIS_LPCOMP_POS + 64)` | Disable MXC_F_LPGCR_PCLKDIS_LPCOMP clock |

### `mxc_sys_system_clock_t`

| 成员 | 说明 |
|---|---|
| `MXC_SYS_CLOCK_IPO = MXC_V_GCR_CLKCTRL_SYSCLK_SEL_IPO` | Select the Internal Primary Oscillator (IPO) |
| `MXC_SYS_CLOCK_IBRO = MXC_V_GCR_CLKCTRL_SYSCLK_SEL_IBRO` | Select the Internal Baud Rate Oscillator (IBRO) |
| `MXC_SYS_CLOCK_ISO = MXC_V_GCR_CLKCTRL_SYSCLK_SEL_ISO` | Select the Internal Secondary Oscillator (ISO) |
| `MXC_SYS_CLOCK_INRO = MXC_V_GCR_CLKCTRL_SYSCLK_SEL_INRO` | Select the Internal Nanoring Oscillator (INRO) |
| `MXC_SYS_CLOCK_ERTCO = MXC_V_GCR_CLKCTRL_SYSCLK_SEL_ERTCO` | Select the External RTC Crystal Oscillator Use the external system clock input |
| `MXC_SYS_CLOCK_EXTCLK = MXC_V_GCR_CLKCTRL_SYSCLK_SEL_EXTCLK` |  |

### `mxc_sys_system_clock_div_t`

| 成员 | 说明 |
|---|---|
| `MXC_SYS_CLOCK_DIV_1 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV1` |  |
| `MXC_SYS_CLOCK_DIV_2 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV2` |  |
| `MXC_SYS_CLOCK_DIV_4 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV4` |  |
| `MXC_SYS_CLOCK_DIV_8 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV8` |  |
| `MXC_SYS_CLOCK_DIV_16 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV16` |  |
| `MXC_SYS_CLOCK_DIV_32 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV32` |  |
| `MXC_SYS_CLOCK_DIV_64 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV64` |  |
| `MXC_SYS_CLOCK_DIV_128 = MXC_S_GCR_CLKCTRL_SYSCLK_DIV_DIV128` |  |

## 宏定义

| 宏 | 值 | 说明 |
|---|---|---|
| `MXC_SYS_USN_CHECKSUM_LEN` | `16` |  |
| `MXC_SYS_USN_CSUM_FIELD_LEN` | `2` |  |
| `MXC_SYS_USN_LEN` | `13` |  |
| `MXC_CRITICAL(code)` | `{     MXC_SYS_Crit_Enter();     code;     MXC_SYS_Crit_Ex...` |  |

## 函数 API

### Function Prototypes

| 函数原型 | 说明 |
|---|---|
| `static inline void _mxc_crit_get_state(void) { uint32_t primask = __get_PRIMASK(); _state.ie_status = (primask == 0); uint32_t mstatus = get_mstatus(); _state.ie_status = ((mstatus & (1 << 3)) != 0)` | 　*头文件内联实现* |
| `static inline void MXC_SYS_Crit_Enter(void) { _mxc_crit_get_state(); if (_state.ie_status) __disable_irq(); _state.in_critical = 1` | Enter a critical section of code that cannot be interrupted. Call @ref MXC_SYS_Crit_Exit to exit the critical section.　*头文件内联实现* |
| `static inline void MXC_SYS_Crit_Exit(void) { if (_state.ie_status) { __enable_irq(); } _state.in_critical = 0; _mxc_crit_get_state()` | Exit a critical section of code from @ref MXC_SYS_Crit_Enter　*头文件内联实现* |
| `static inline int MXC_SYS_In_Crit_Section(void) { return _state.in_critical` | Polls whether code is currently executing from a critical section.　*头文件内联实现* |
| `int MXC_SYS_GetUSN(uint8_t *usn, uint8_t *checksum)` | Reads the device USN and verifies the checksum. |
| `int MXC_SYS_IsClockEnabled(mxc_sys_periph_clock_t clock)` | Determines if the selected peripheral clock is enabled. |
| `void MXC_SYS_ClockDisable(mxc_sys_periph_clock_t clock)` | Disables the selected peripheral clock. |
| `void MXC_SYS_ClockEnable(mxc_sys_periph_clock_t clock)` | Enables the selected peripheral clock. |
| `void MXC_SYS_RTCClockEnable(void)` | Enables the 32kHz oscillator |
| `int MXC_SYS_RTCClockDisable(void)` | Disables the 32kHz oscillator |
| `int MXC_SYS_ClockSourceEnable(mxc_sys_system_clock_t clock)` | Enable System Clock Source without switching to it |
| `int MXC_SYS_ClockSourceDisable(mxc_sys_system_clock_t clock)` | Disable System Clock Source |
| `mxc_sys_system_clock_div_t MXC_SYS_GetClockDiv(void)` | Get the current system clock divider. |
| `void MXC_SYS_SetClockDiv(mxc_sys_system_clock_div_t div)` | Set the system clock divider. |
| `int MXC_SYS_Clock_Select(mxc_sys_system_clock_t clock)` | Select the system clock. |
| `int MXC_SYS_Clock_Timeout(uint32_t ready)` | Wait for a clock to enable with timeout |
| `void MXC_SYS_Reset_Periph(mxc_sys_reset_t reset)` | Reset the peripherals and/or CPU in the rstr0 or rstr1 register. |
| `void MXC_SYS_RISCVRun(void)` | Setup and run RISCV core |
| `void MXC_SYS_RISCVShutdown(void)` | Shutdown the RISCV core |
| `uint32_t MXC_SYS_RiscVClockRate(void)` | Returns the clock rate (in Hz) of the Risc-V core. |
| `int MXC_SYS_LockDAP_Permanent(void)` | This function PERMANENTLY locks the Debug Access Port. |

## 依赖的其他头文件

- `mxc_device.h`
- `lpgcr_regs.h`
- `gcr_regs.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `mxc_sys.h` 自动生成，请勿手改；改脚本后重跑。*
