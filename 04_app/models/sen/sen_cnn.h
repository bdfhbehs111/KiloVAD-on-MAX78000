/**************************************************************************************************
* Copyright (C) 2019-2021 Maxim Integrated Products, Inc. All Rights Reserved.
*
* Maxim Integrated Products, Inc. Default Copyright Notice:
* https://www.maximintegrated.com/en/aboutus/legal/copyrights.html
**************************************************************************************************/

/*
 * This header file was automatically @generated for the sentinel network from a template.
 * Please do not edit; instead, edit the template and regenerate.
 */

#ifndef __SEN_CNN_H__
#define __SEN_CNN_H__

#include <stdint.h>
#include "model_common.h"

/* Return codes */
#define SEN_CNN_FAIL 0
#define SEN_CNN_OK 1

/*
  SUMMARY OF OPS
  Hardware: 162,848 ops (158,752 macc; 3,840 comp; 256 add; 0 mul; 0 bitwise)
    Layer 0: 132,096 ops (131,072 macc; 1,024 comp; 0 add; 0 mul; 0 bitwise)
    Layer 1: 20,224 ops (18,432 macc; 1,792 comp; 0 add; 0 mul; 0 bitwise)
    Layer 2: 10,240 ops (9,216 macc; 1,024 comp; 0 add; 0 mul; 0 bitwise)
    Layer 3: 256 ops (0 macc; 0 comp; 256 add; 0 mul; 0 bitwise)
    Layer 4: 32 ops (32 macc; 0 comp; 0 add; 0 mul; 0 bitwise)

  RESOURCE USAGE
  Weight memory: 1,920 bytes out of 442,368 bytes total (0.4%)
  Bias memory:   38 bytes out of 2,048 bytes total (1.9%)
*/

/* Number of outputs for this network */
#define SEN_CNN_NUM_OUTPUTS 1

/* Port pin actions used to signal that processing is active */

#define SEN_CNN_START LED_On(1)
#define SEN_CNN_COMPLETE LED_Off(1)
#define SEN_SYS_START LED_On(0)
#define SEN_SYS_COMPLETE LED_Off(0)



/* Stopwatch - holds the runtime when accelerator finishes */
extern volatile uint32_t sen_cnn_time;

/* Custom memcopy routines used for weights and data */
void sen_memcpy32(uint32_t *dst, const uint32_t *src, int n);
void sen_memcpy32_const(uint32_t *dst, int n);

/* Enable clocks and power to accelerator, enable interrupt */
int sen_cnn_enable(uint32_t clock_source, uint32_t clock_divider);

/* Disable clocks and power to accelerator */
int sen_cnn_disable(void);

/* Perform minimum accelerator initialization so it can be configured */
int sen_cnn_init(void);

/* Configure accelerator for the given network */
int sen_cnn_configure(void);

/* Load accelerator weights */
int sen_cnn_load_weights(void);

/* Verify accelerator weights (debug only) */
int sen_cnn_verify_weights(void);

/* Load accelerator bias values (if needed) */
int sen_cnn_load_bias(void);

/* Start accelerator processing */
int sen_cnn_start(void);

/* Force stop accelerator */
int sen_cnn_stop(void);

/* Continue accelerator after stop */
int sen_cnn_continue(void);

/* Unload results from accelerator */
int sen_cnn_unload(uint32_t *out_buf);

/* Turn on the boost circuit */
int sen_cnn_boost_enable(mxc_gpio_regs_t *port, uint32_t pin);

/* Turn off the boost circuit */
int sen_cnn_boost_disable(mxc_gpio_regs_t *port, uint32_t pin);

#endif // __SEN_CNN_H__
