/**************************************************************************************************
* Copyright (C) 2019-2021 Maxim Integrated Products, Inc. All Rights Reserved.
*
* Maxim Integrated Products, Inc. Default Copyright Notice:
* https://www.maximintegrated.com/en/aboutus/legal/copyrights.html
**************************************************************************************************/

/*
 * This header file was automatically @generated for the vad_cnn network from a template.
 * Please do not edit; instead, edit the template and regenerate.
 */

#ifndef __VAD_CNN_H__
#define __VAD_CNN_H__

#include <stdint.h>
#include "model_common.h"

/* Return codes */
#define VAD_CNN_FAIL 0
#define VAD_CNN_OK 1

/*
  SUMMARY OF OPS
  Hardware: 814,512 ops (800,928 macc; 13,584 comp; 0 add; 0 mul; 0 bitwise)
    Layer 0 (conv1_Conv_8): 528,384 ops (524,288 macc; 4,096 comp; 0 add; 0 mul; 0 bitwise)
    Layer 1 (conv2_Conv_6): 153,088 ops (147,456 macc; 5,632 comp; 0 add; 0 mul; 0 bitwise)
    Layer 2 (conv3_Conv_6): 76,288 ops (73,728 macc; 2,560 comp; 0 add; 0 mul; 0 bitwise)
    Layer 3 (conv4_Conv_6): 49,664 ops (49,152 macc; 512 comp; 0 add; 0 mul; 0 bitwise)
    Layer 4 (conv5_Conv_6): 6,784 ops (6,144 macc; 640 comp; 0 add; 0 mul; 0 bitwise)
    Layer 5 (conv6_Conv_6): 272 ops (128 macc; 144 comp; 0 add; 0 mul; 0 bitwise)
    Layer 6 (fc_MatMul_3): 32 ops (32 macc; 0 comp; 0 add; 0 mul; 0 bitwise)

  RESOURCE USAGE
  Weight memory: 10,784 bytes out of 442,368 bytes total (2.4%)
  Bias memory:   130 bytes out of 2,048 bytes total (6.3%)
*/

/* Number of outputs for this network */
#define VAD_CNN_NUM_OUTPUTS 1

/* Port pin actions used to signal that processing is active */

#define VAD_CNN_START LED_On(1)
#define VAD_CNN_COMPLETE LED_Off(1)
#define VAD_SYS_START LED_On(0)
#define VAD_SYS_COMPLETE LED_Off(0)

/* Stopwatch - holds the runtime when accelerator finishes */
extern volatile uint32_t vad_cnn_time;

/* Custom memcopy routines used for weights and data */
void vad_cnn_memcpy32(uint32_t *dst, const uint32_t *src, int n);
void vad_cnn_memcpy32_const(uint32_t *dst, int n);

/* Enable clocks and power to accelerator, enable interrupt */
int vad_cnn_enable(uint32_t clock_source, uint32_t clock_divider);

/* Disable clocks and power to accelerator */
int vad_cnn_disable(void);

/* Perform minimum accelerator initialization so it can be configured */
int vad_cnn_init(void);

/* Configure accelerator for the given network */
int vad_cnn_configure(void);

/* Load accelerator weights */
int vad_cnn_load_weights(void);

/* Verify accelerator weights (debug only) */
int vad_cnn_verify_weights(void);

/* Load accelerator bias values (if needed) */
int vad_cnn_load_bias(void);

/* Start accelerator processing */
int vad_cnn_start(void);

/* Force stop accelerator */
int vad_cnn_stop(void);

/* Continue accelerator after stop */
int vad_cnn_continue(void);

/* Unload results from accelerator */
int vad_cnn_unload(uint32_t *out_buf);

/* Turn on the boost circuit */
int vad_cnn_boost_enable(mxc_gpio_regs_t *port, uint32_t pin);

/* Turn off the boost circuit */
int vad_cnn_boost_disable(mxc_gpio_regs_t *port, uint32_t pin);

#endif // __VAD_CNN_H__
