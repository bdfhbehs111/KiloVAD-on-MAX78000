/**************************************************************************************************
* Copyright (C) 2019-2021 Maxim Integrated Products, Inc. All Rights Reserved.
*
* Maxim Integrated Products, Inc. Default Copyright Notice:
* https://www.maximintegrated.com/en/aboutus/legal/copyrights.html
**************************************************************************************************/

/*
 * This header file was automatically @generated for the kws26 network from a template.
 * Please do not edit; instead, edit the template and regenerate.
 */

#ifndef __KWS_CNN_H__
#define __KWS_CNN_H__

#include <stdint.h>
#include "model_common.h"

/* Return codes */
#define KWS_CNN_FAIL 0
#define KWS_CNN_OK 1

/*
  SUMMARY OF OPS
  Hardware: 1,893,280 ops (1,878,656 macc; 14,624 comp; 0 add; 0 mul; 0 bitwise)
    Layer 0: 1,552,320 ops (1,548,288 macc; 4,032 comp; 0 add; 0 mul; 0 bitwise)
    Layer 1: 297,360 ops (290,304 macc; 7,056 comp; 0 add; 0 mul; 0 bitwise)
    Layer 2: 35,504 ops (32,256 macc; 3,248 comp; 0 add; 0 mul; 0 bitwise)
    Layer 3: 6,432 ops (6,144 macc; 288 comp; 0 add; 0 mul; 0 bitwise)
    Layer 4: 1,664 ops (1,664 macc; 0 comp; 0 add; 0 mul; 0 bitwise)

  RESOURCE USAGE
  Weight memory: 29,312 bytes out of 442,368 bytes total (6.6%)
  Bias memory:   202 bytes out of 2,048 bytes total (9.9%)
*/

/* Number of outputs for this network */
#define KWS_CNN_NUM_OUTPUTS 26

/* Port pin actions used to signal that processing is active */

#define KWS_CNN_START LED_On(1)
#define KWS_CNN_COMPLETE LED_Off(1)
#define KWS_SYS_START LED_On(0)
#define KWS_SYS_COMPLETE LED_Off(0)



/* Stopwatch - holds the runtime when accelerator finishes */
extern volatile uint32_t kws_cnn_time;

/* Custom memcopy routines used for weights and data */
void kws_memcpy32(uint32_t *dst, const uint32_t *src, int n);
void kws_memcpy32_const(uint32_t *dst, int n);

/* Enable clocks and power to accelerator, enable interrupt */
int kws_cnn_enable(uint32_t clock_source, uint32_t clock_divider);

/* Disable clocks and power to accelerator */
int kws_cnn_disable(void);

/* Perform minimum accelerator initialization so it can be configured */
int kws_cnn_init(void);

/* Configure accelerator for the given network */
int kws_cnn_configure(void);

/* Load accelerator weights */
int kws_cnn_load_weights(void);

/* Verify accelerator weights (debug only) */
int kws_cnn_verify_weights(void);

/* Load accelerator bias values (if needed) */
int kws_cnn_load_bias(void);

/* Start accelerator processing */
int kws_cnn_start(void);

/* Force stop accelerator */
int kws_cnn_stop(void);

/* Continue accelerator after stop */
int kws_cnn_continue(void);

/* Unload results from accelerator */
int kws_cnn_unload(uint32_t *out_buf);

/* Turn on the boost circuit */
int kws_cnn_boost_enable(mxc_gpio_regs_t *port, uint32_t pin);

/* Turn off the boost circuit */
int kws_cnn_boost_disable(mxc_gpio_regs_t *port, uint32_t pin);

#endif // __KWS_CNN_H__
