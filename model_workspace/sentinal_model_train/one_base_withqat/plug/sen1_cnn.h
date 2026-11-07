/**************************************************************************************************
* Copyright (C) 2019-2021 Maxim Integrated Products, Inc. All Rights Reserved.
*
* Maxim Integrated Products, Inc. Default Copyright Notice:
* https://www.maximintegrated.com/en/aboutus/legal/copyrights.html
**************************************************************************************************/

/*
 * This header file was automatically @generated for the sen1_cnn network from a template.
 * Please do not edit; instead, edit the template and regenerate.
 */

#ifndef __SEN1_CNN_H__
#define __SEN1_CNN_H__

#include <stdint.h>
#include "model_common.h"

/* Return codes */
#define SEN1_CNN_FAIL 0
#define SEN1_CNN_OK 1

/*
  SUMMARY OF OPS
  Hardware: 3,838,512 ops (3,801,632 macc; 36,880 comp; 0 add; 0 mul; 0 bitwise)
    Layer 0 (conv1_Conv_8): 1,056,768 ops (1,048,576 macc; 8,192 comp; 0 add; 0 mul; 0 bitwise)
    Layer 1 (conv2_Conv_6): 1,193,984 ops (1,179,648 macc; 14,336 comp; 0 add; 0 mul; 0 bitwise)
    Layer 2 (conv3_Conv_6): 893,952 ops (884,736 macc; 9,216 comp; 0 add; 0 mul; 0 bitwise)
    Layer 3 (conv4_Conv_6): 591,872 ops (589,824 macc; 2,048 comp; 0 add; 0 mul; 0 bitwise)
    Layer 4 (conv5_Conv_6): 100,864 ops (98,304 macc; 2,560 comp; 0 add; 0 mul; 0 bitwise)
    Layer 5 (conv6_Conv_6): 1,040 ops (512 macc; 528 comp; 0 add; 0 mul; 0 bitwise)
    Layer 6 (fc_MatMul_3): 32 ops (32 macc; 0 comp; 0 add; 0 mul; 0 bitwise)

  RESOURCE USAGE
  Weight memory: 79,392 bytes out of 442,368 bytes total (17.9%)
  Bias memory:   370 bytes out of 2,048 bytes total (18.1%)
*/

/* Number of outputs for this network */
#define SEN1_CNN_NUM_OUTPUTS 1

/* Port pin actions used to signal that processing is active */

#define SEN1_CNN_START LED_On(1)
#define SEN1_CNN_COMPLETE LED_Off(1)
#define SEN1_SYS_START LED_On(0)
#define SEN1_SYS_COMPLETE LED_Off(0)

/* Stopwatch - holds the runtime when accelerator finishes */
extern volatile uint32_t sen1_cnn_time;

/* Custom memcopy routines used for weights and data */
void sen1_memcpy32(uint32_t *dst, const uint32_t *src, int n);
void sen1_memcpy32_const(uint32_t *dst, int n);

/* Enable clocks and power to accelerator, enable interrupt */
int sen1_cnn_enable(uint32_t clock_source, uint32_t clock_divider);

/* Disable clocks and power to accelerator */
int sen1_cnn_disable(void);

/* Perform minimum accelerator initialization so it can be configured */
int sen1_cnn_init(void);

/* Configure accelerator for the given network */
int sen1_cnn_configure(void);

/* Load accelerator weights */
int sen1_cnn_load_weights(void);

/* Verify accelerator weights (debug only) */
int sen1_cnn_verify_weights(void);

/* Load accelerator bias values (if needed) */
int sen1_cnn_load_bias(void);

/* Start accelerator processing */
int sen1_cnn_start(void);

/* Force stop accelerator */
int sen1_cnn_stop(void);

/* Continue accelerator after stop */
int sen1_cnn_continue(void);

/* Unload results from accelerator */
int sen1_cnn_unload(uint32_t *out_buf);

/* Turn on the boost circuit */
int sen1_cnn_boost_enable(mxc_gpio_regs_t *port, uint32_t pin);

/* Turn off the boost circuit */
int sen1_cnn_boost_disable(mxc_gpio_regs_t *port, uint32_t pin);

#endif // __SEN1_CNN_H__
