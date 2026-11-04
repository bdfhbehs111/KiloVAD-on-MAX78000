/**
 * @file    model_common.h
 * @brief   两个模型**完全相同**的部分：定点类型 + 共享 softmax。
 *
 * ⚠ 本文件由 04_app/tools/namespace_models.py 自动生成，请勿手改。
 *
 * 背景：ai8xize 会把 `q31_t` / `q15_t` 的 typedef 和 softmax 原型塞进
 * 每个模型的 cnn.h。两个模型各有一份 → 改名后若都 include 就会重复定义。
 * 这里抽成唯一来源，{sen,kws}_cnn.h 都 #include 它。
 */

#ifndef MODEL_COMMON_H_
#define MODEL_COMMON_H_

#include <stdint.h>

/* 定点类型（原本在 ai8xize 生成的 cnn.h 里） */
#ifndef MODEL_Q_TYPES_DEFINED
#define MODEL_Q_TYPES_DEFINED
typedef int32_t q31_t;
typedef int16_t q15_t;
#endif /* MODEL_Q_TYPES_DEFINED */

/* 定点 softmax（实现在 models/softmax.c，两个模型共用一份） */
void softmax_q17p14_q15(const q31_t *vec_in, const uint16_t dim_vec, q15_t *p_out);
void softmax_shift_q17p14_q15(q31_t *vec_in, const uint16_t dim_vec, uint8_t in_shift, q15_t *p_out);

#endif /* MODEL_COMMON_H_ */
