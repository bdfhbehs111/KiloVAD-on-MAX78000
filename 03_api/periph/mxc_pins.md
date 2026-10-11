# `mxc_pins.h` — 引脚映射

> **概要**：This file contains constant pin configurations for the peripherals.
> **头文件**：`03_api/headers/mxc_pins.h`
> **驱动实现**：`03_api/source_ai85/SYS/`
> **函数** 0　**宏** 0　**枚举** 0　**结构体** 0　**全局变量** 64

---

## 目录

- [预定义全局变量](#预定义全局变量)
- [函数 API](#函数-api)
- [依赖的其他头文件](#依赖的其他头文件)

## 预定义全局变量

> SDK 已定义好的配置对象，直接取地址传给初始化函数即可，无需自己填。

| 变量 | 声明 |
|---|---|
| `gpio_cfg_extclk` | `const mxc_gpio_cfg_t gpio_cfg_extclk` |
| `gpio_cfg_i2c0` | `const mxc_gpio_cfg_t gpio_cfg_i2c0` |
| `gpio_cfg_i2c1` | `const mxc_gpio_cfg_t gpio_cfg_i2c1` |
| `gpio_cfg_i2c2` | `const mxc_gpio_cfg_t gpio_cfg_i2c2` |
| `gpio_cfg_uart0` | `const mxc_gpio_cfg_t gpio_cfg_uart0` |
| `gpio_cfg_uart0_flow` | `const mxc_gpio_cfg_t gpio_cfg_uart0_flow` |
| `gpio_cfg_uart0_flow_disable` | `const mxc_gpio_cfg_t gpio_cfg_uart0_flow_disable` |
| `gpio_cfg_uart1` | `const mxc_gpio_cfg_t gpio_cfg_uart1` |
| `gpio_cfg_uart2` | `const mxc_gpio_cfg_t gpio_cfg_uart2` |
| `gpio_cfg_uart3` | `const mxc_gpio_cfg_t gpio_cfg_uart3` |
| `gpio_cfg_tmr0` | `const mxc_gpio_cfg_t gpio_cfg_tmr0` |
| `gpio_cfg_tmr1` | `const mxc_gpio_cfg_t gpio_cfg_tmr1` |
| `gpio_cfg_tmr2` | `const mxc_gpio_cfg_t gpio_cfg_tmr2` |
| `gpio_cfg_tmr3` | `const mxc_gpio_cfg_t gpio_cfg_tmr3` |
| `gpio_cfg_tmr0b` | `const mxc_gpio_cfg_t gpio_cfg_tmr0b` |
| `gpio_cfg_tmr1b` | `const mxc_gpio_cfg_t gpio_cfg_tmr1b` |
| `gpio_cfg_tmr2b` | `const mxc_gpio_cfg_t gpio_cfg_tmr2b` |
| `gpio_cfg_tmr3b` | `const mxc_gpio_cfg_t gpio_cfg_tmr3b` |
| `gpio_cfg_tmr4` | `const mxc_gpio_cfg_t gpio_cfg_tmr4` |
| `gpio_cfg_tmr5` | `const mxc_gpio_cfg_t gpio_cfg_tmr5` |
| `gpio_cfg_i2s0` | `const mxc_gpio_cfg_t gpio_cfg_i2s0` |
| `gpio_cfg_i2s0_extclk` | `const mxc_gpio_cfg_t gpio_cfg_i2s0_extclk` |
| `gpio_cfg_owm` | `const mxc_gpio_cfg_t gpio_cfg_owm` |
| `gpio_cfg_owmb` | `const mxc_gpio_cfg_t gpio_cfg_owmb` |
| `gpio_cfg_spi0` | `const mxc_gpio_cfg_t gpio_cfg_spi0` |
| `gpio_cfg_spi1` | `const mxc_gpio_cfg_t gpio_cfg_spi1` |
| `gpio_cfg_rtcsqw` | `const mxc_gpio_cfg_t gpio_cfg_rtcsqw` |
| `gpio_cfg_rtcsqwb` | `const mxc_gpio_cfg_t gpio_cfg_rtcsqwb` |
| `gpio_cfg_pt0` | `const mxc_gpio_cfg_t gpio_cfg_pt0` |
| `gpio_cfg_pt1` | `const mxc_gpio_cfg_t gpio_cfg_pt1` |
| `gpio_cfg_pt2` | `const mxc_gpio_cfg_t gpio_cfg_pt2` |
| `gpio_cfg_pt3` | `const mxc_gpio_cfg_t gpio_cfg_pt3` |
| `gpio_cfg_pcif_P0_BITS_0_7` | `const mxc_gpio_cfg_t gpio_cfg_pcif_P0_BITS_0_7` |
| `gpio_cfg_pcif_P0_BITS_8_9` | `const mxc_gpio_cfg_t gpio_cfg_pcif_P0_BITS_8_9` |
| `gpio_cfg_pcif_P1_BITS_10_11` | `const mxc_gpio_cfg_t gpio_cfg_pcif_P1_BITS_10_11` |
| `gpio_cfg_pcif_hsync` | `const mxc_gpio_cfg_t gpio_cfg_pcif_hsync` |
| `gpio_cfg_pcif_vsync` | `const mxc_gpio_cfg_t gpio_cfg_pcif_vsync` |
| `gpio_cfg_pcif_xclk` | `const mxc_gpio_cfg_t gpio_cfg_pcif_xclk` |
| `gpio_cfg_adc_ain0` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain0` |
| `gpio_cfg_adc_ain1` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain1` |
| `gpio_cfg_adc_ain2` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain2` |
| `gpio_cfg_adc_ain3` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain3` |
| `gpio_cfg_adc_ain4` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain4` |
| `gpio_cfg_adc_ain4` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain4` |
| `gpio_cfg_adc_ain5` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain5` |
| `gpio_cfg_adc_ain6` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain6` |
| `gpio_cfg_adc_ain7` | `const mxc_gpio_cfg_t gpio_cfg_adc_ain7` |
| `gpio_cfg_rv_jtag` | `const mxc_gpio_cfg_t gpio_cfg_rv_jtag` |
| `gpio_cfg_cmp0` | `const mxc_gpio_cfg_t gpio_cfg_cmp0` |
| `gpio_cfg_cmp1` | `const mxc_gpio_cfg_t gpio_cfg_cmp1` |
| `gpio_cfg_cmp2` | `const mxc_gpio_cfg_t gpio_cfg_cmp2` |
| `gpio_cfg_cmp3` | `const mxc_gpio_cfg_t gpio_cfg_cmp3` |
| `gpio_cfg_spi0_standard` | `const mxc_gpio_cfg_t gpio_cfg_spi0_standard` |
| `gpio_cfg_spi0_3wire` | `const mxc_gpio_cfg_t gpio_cfg_spi0_3wire` |
| `gpio_cfg_spi0_dual` | `const mxc_gpio_cfg_t gpio_cfg_spi0_dual` |
| `gpio_cfg_spi0_quad` | `const mxc_gpio_cfg_t gpio_cfg_spi0_quad` |
| `gpio_cfg_spi1_standard` | `const mxc_gpio_cfg_t gpio_cfg_spi1_standard` |
| `gpio_cfg_spi1_3wire` | `const mxc_gpio_cfg_t gpio_cfg_spi1_3wire` |
| `gpio_cfg_spi1_dual` | `const mxc_gpio_cfg_t gpio_cfg_spi1_dual` |
| `gpio_cfg_spi1_quad` | `const mxc_gpio_cfg_t gpio_cfg_spi1_quad` |
| `gpio_cfg_spi0_ts0` | `const mxc_gpio_cfg_t gpio_cfg_spi0_ts0` |
| `gpio_cfg_spi0_ts1` | `const mxc_gpio_cfg_t gpio_cfg_spi0_ts1` |
| `gpio_cfg_spi0_ts2` | `const mxc_gpio_cfg_t gpio_cfg_spi0_ts2` |
| `gpio_cfg_spi1_ts0` | `const mxc_gpio_cfg_t gpio_cfg_spi1_ts0` |

## 函数 API

_（本头文件无函数声明）_

## 依赖的其他头文件

- `gpio.h`

---

*本文件由 `03_api/tools/gen_api_docs.py` 从 `mxc_pins.h` 自动生成，请勿手改；改脚本后重跑。*
