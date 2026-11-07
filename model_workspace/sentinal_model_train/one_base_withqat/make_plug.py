"""把 ai8xize 生成的 cnn.c/cnn.h/weights.h 变成可无缝接入 04_app 的 sen1_cnn_* 文件。

只做机械重命名 + FreeRTOS ISR 接线 + 头文件去重，不改模型内容。
"""
import os
import re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sen1_cnn')
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plug')
os.makedirs(DST, exist_ok=True)

# ---------- 通用词法重命名（顺序：先长后短，避免 cnn_time 被 cnn_ 先吃掉） ----------
def rename_common(text: str) -> str:
    # 头文件 include
    text = text.replace('#include "cnn.h"', '#include "sen1_cnn.h"')
    text = text.replace('#include "weights.h"', '#include "sen1_cnn_weights.h"')
    # 宏
    for a, b in [('CNN_NUM_OUTPUTS', 'SEN1_CNN_NUM_OUTPUTS'),
                 ('CNN_FAIL', 'SEN1_CNN_FAIL'),
                 ('CNN_OK', 'SEN1_CNN_OK'),
                 ('CNN_START', 'SEN1_CNN_START'),
                 ('CNN_COMPLETE', 'SEN1_CNN_COMPLETE'),
                 ('SYS_START', 'SEN1_SYS_START'),
                 ('SYS_COMPLETE', 'SEN1_SYS_COMPLETE')]:
        text = re.sub(r'\b' + a + r'\b', b, text)
    # 函数/变量：cnn_time 先处理，再 cnn_*
    text = re.sub(r'\bcnn_time\b', 'sen1_cnn_time', text)
    text = re.sub(r'\bcnn_(\w+)', r'sen1_cnn_\1', text)
    # memcpy32（只改对外两个，static 的 memcpy_8to32 不动）
    text = re.sub(r'\bmemcpy32_const\b', 'sen1_memcpy32_const', text)
    text = re.sub(r'\bmemcpy32\b', 'sen1_memcpy32', text)
    return text


# ---------------- cnn.c ----------------
with open(os.path.join(SRC, 'cnn.c'), 'r', encoding='utf-8') as f:
    c = f.read()

# 1) 加 FreeRTOS / 任务头 + extern cnn_isr（放在 gcfr_regs.h 之后）
c = c.replace('#include "gcfr_regs.h"\n#include "cnn.h"\n#include "weights.h"',
              '#include "gcfr_regs.h"\n#include "sen1_cnn.h"\n#include "sen1_cnn_weights.h"\n\n'
              '#include "FreeRTOS.h"\n#include "task.h"\n#include "semphr.h"\n\n'
              'extern TaskHandle_t cnn_isr;')

# 2) 用 FreeRTOS 版 ISR 替换 ai8xize 原始 ISR（原始块精确匹配）
old_isr = '''void CNN_ISR(void)
{
  // Acknowledge interrupt to all quadrants
  *((volatile uint32_t *) 0x50100000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50500000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50900000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50d00000) &= ~((1<<12) | 1);

  CNN_COMPLETE; // Signal that processing is complete
#ifdef CNN_INFERENCE_TIMER
  cnn_time = MXC_TMR_SW_Stop(CNN_INFERENCE_TIMER);
#else
  cnn_time = 1;
#endif
}'''
new_isr = '''void CNN_ISR(void)
{
  // Acknowledge interrupt to all quadrants
  *((volatile uint32_t *) 0x50100000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50500000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50900000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50d00000) &= ~((1<<12) | 1);

  SEN1_CNN_COMPLETE;           /* LED1 off, inference done */
  sen1_cnn_time = 1;

  /* Notify the CNN task (tasks_manage.c waits with ulTaskNotifyTake) */
  {
    BaseType_t higher_woken = pdFALSE;
    vTaskNotifyGiveFromISR(cnn_isr, &higher_woken);
    portYIELD_FROM_ISR(higher_woken);
  }
}'''
assert old_isr in c, 'ISR 块没匹配上，检查 cnn.c'
c = c.replace(old_isr, new_isr)

# 3) 词法重命名
c = rename_common(c)
# cnn_isr 是 tasks_manage.c 里的任务句柄，不能被改名
c = c.replace('sen1_cnn_isr', 'cnn_isr')

# 3.5) CNN 中断优先级 —— 必须补，否则上板第一次推理就死
#   MXC_NVIC_SetVector 只做「装向量 + NVIC_EnableIRQ」，从不设优先级；
#   NVIC 复位优先级是 0（最高），而 CNN_ISR 里要调 vTaskNotifyGiveFromISR，
#   FreeRTOS 要求能调 FromISR 的中断，优先级数值必须 >=
#   configMAX_SYSCALL_INTERRUPT_PRIORITY（本工程 FreeRTOSConfig.h 里 = 5）。
#   0 < 5 → vPortValidateInterruptPriority 触发 configASSERT
#   （taskDISABLE_INTERRUPTS(); for(;;){}），整颗 CPU 卡死、串口再无输出。
c = c.replace(
    '  MXC_NVIC_SetVector(CNN_IRQn, CNN_ISR); // Set CNN complete vector',
    '  NVIC_SetPriority(CNN_IRQn, 5);             /* FreeRTOS: 必须 >= configMAX_SYSCALL */\n'
    '  MXC_NVIC_SetVector(CNN_IRQn, CNN_ISR); // Set CNN complete vector',
)

# 3.6) sen1_cnn_time 的定义原本在 ai8xize 生成的 main.c 里，plug 只带了 extern 声明
c = c.replace(
    'extern TaskHandle_t cnn_isr;',
    'volatile uint32_t sen1_cnn_time;   /* 头文件里是 extern，这里给定义 */\n\n'
    'extern TaskHandle_t cnn_isr;',
)

# 输出格式对齐现役 sen_cnn：去掉 <<5，raw int8（解码无需改）
c = c.replace('''  *out_buf++ = (int16_t)((val & 0xff)) << 5;
  *out_buf++ = (int16_t)(((val >> 8) & 0xff)) << 5;''',
              '''  *out_buf++ = (val & 0xff);
  *out_buf++ = ((val >> 8) & 0xff);''')

with open(os.path.join(DST, 'sen1_cnn.c'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)


# ---------------- cnn.h ----------------
with open(os.path.join(SRC, 'cnn.h'), 'r', encoding='utf-8') as f:
    h = f.read()

h = rename_common(h)
# 头文件保护宏改名，避免与别的 cnn.h 撞
h = h.replace('#ifndef __CNN_H__', '#ifndef __SEN1_CNN_H__').replace('#define __CNN_H__', '#define __SEN1_CNN_H__')
h = h.replace('#endif // __CNN_H__', '#endif // __SEN1_CNN_H__')
# q31_t/q15_t + softmax 都来自 model_common.h（避免与 sen_cnn.h 重复定义）
h = h.replace('#include <stdint.h>\ntypedef int32_t q31_t;\ntypedef int16_t q15_t;',
              '#include <stdint.h>\n#include "model_common.h"')
# 删掉重复的 softmax 声明（model_common.h 已有）
h = re.sub(r'/\* Run software SoftMax on unloaded data \*/\nvoid softmax_q17p14_q15[^\n]*\n/\* Shift the input[^\n]*\nvoid softmax_shift_q17p14_q15[^\n]*\n\n?', '', h)

with open(os.path.join(DST, 'sen1_cnn.h'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(h)


# ---------------- weights.h ----------------
with open(os.path.join(SRC, 'weights.h'), 'r', encoding='utf-8') as f:
    w = f.read()
with open(os.path.join(DST, 'sen1_cnn_weights.h'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(w)

print('done ->', DST)
for name in os.listdir(DST):
    print(' ', name, os.path.getsize(os.path.join(DST, name)))
