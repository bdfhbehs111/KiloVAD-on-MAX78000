"""把 ai8xize 生成的 cnn.c/cnn.h/weights.h 变成可无缝接入项目的 vad_cnn_* 文件。

和 one_base_withqat/make_plug.py 同一套机械变换，只把 sen1 -> vad，另外多改一处：

    ISR 函数名 CNN_ISR -> VAD_CNN_ISR

原因：sen1_cnn.c 里已经定义了 `void CNN_ISR(void)`。两个模型文件同时参与编译时，
两个同名非 static 函数会在链接期报 duplicate symbol。改名后 vad_cnn.c 自己
MXC_NVIC_SetVector(CNN_IRQn, VAD_CNN_ISR)，对 app 完全透明（app 只调 vad_cnn_init/start）。

其余注入（与 sen1 完全一致，少一条上板就死）：
    1) NVIC_SetPriority(CNN_IRQn, 5)   —— MXC_NVIC_SetVector 不设优先级，
       NVIC 复位值 0 < configMAX_SYSCALL_INTERRUPT_PRIORITY(5)，
       ISR 里调 vTaskNotifyGiveFromISR 会触发 configASSERT -> 整机卡死
    2) volatile uint32_t vad_cnn_time; —— 头文件里是 extern，定义原本在 ai8xize 的
       main.c 里，plug 不带 main.c，不给定义就 undefined reference
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'vad_cnn')
DST = os.path.join(BASE, 'plug')
os.makedirs(DST, exist_ok=True)

PREFIX = 'vad_cnn'


def rename_common(text: str) -> str:
    text = text.replace('#include "cnn.h"', f'#include "{PREFIX}.h"')
    text = text.replace('#include "weights.h"', f'#include "{PREFIX}_weights.h"')
    for a, b in [('CNN_NUM_OUTPUTS', 'VAD_CNN_NUM_OUTPUTS'),
                 ('CNN_FAIL', 'VAD_CNN_FAIL'),
                 ('CNN_OK', 'VAD_CNN_OK'),
                 ('CNN_START', 'VAD_CNN_START'),
                 ('CNN_COMPLETE', 'VAD_CNN_COMPLETE'),
                 ('SYS_START', 'VAD_SYS_START'),
                 ('SYS_COMPLETE', 'VAD_SYS_COMPLETE')]:
        text = re.sub(r'\b' + a + r'\b', b, text)
    text = re.sub(r'\bcnn_time\b', 'vad_cnn_time', text)
    text = re.sub(r'\bcnn_(\w+)', rf'{PREFIX}_\1', text)
    text = re.sub(r'\bmemcpy32_const\b', f'{PREFIX}_memcpy32_const', text)
    text = re.sub(r'\bmemcpy32\b', f'{PREFIX}_memcpy32', text)
    # ISR 改名，避免与 sen1_cnn.c 的 CNN_ISR 撞符号
    text = re.sub(r'\bCNN_ISR\b', 'VAD_CNN_ISR', text)
    return text


# ---------------- cnn.c ----------------
with open(os.path.join(SRC, 'cnn.c'), 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('#include "gcfr_regs.h"\n#include "cnn.h"\n#include "weights.h"',
              f'#include "gcfr_regs.h"\n#include "{PREFIX}.h"\n#include "{PREFIX}_weights.h"\n\n'
              '#include "FreeRTOS.h"\n#include "task.h"\n#include "semphr.h"\n\n'
              'extern TaskHandle_t cnn_isr;')
assert 'FreeRTOS.h' in c, 'cnn.c 的 include 块没匹配上'

# FreeRTOS 版 ISR：通知 cnn 任务
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
new_isr = '''void VAD_CNN_ISR(void)
{
  // Acknowledge interrupt to all quadrants
  *((volatile uint32_t *) 0x50100000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50500000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50900000) &= ~((1<<12) | 1);
  *((volatile uint32_t *) 0x50d00000) &= ~((1<<12) | 1);

  VAD_CNN_COMPLETE;            /* LED1 off, inference done */
  vad_cnn_time = 1;

  /* Notify the CNN task (tasks_manage.c waits with ulTaskNotifyTake) */
  {
    BaseType_t higher_woken = pdFALSE;
    vTaskNotifyGiveFromISR(cnn_isr, &higher_woken);
    portYIELD_FROM_ISR(higher_woken);
  }
}'''
assert old_isr in c, 'cnn.c 的 CNN_ISR 块没匹配上'
c = c.replace(old_isr, new_isr)

c = rename_common(c)
c = c.replace('vad_cnn_isr', 'cnn_isr')          # 任务句柄不能被改名

# 优先级：必须补
c = c.replace(
    '  MXC_NVIC_SetVector(CNN_IRQn, VAD_CNN_ISR); // Set CNN complete vector',
    '  NVIC_SetPriority(CNN_IRQn, 5);             /* FreeRTOS: 必须 >= configMAX_SYSCALL */\n'
    '  MXC_NVIC_SetVector(CNN_IRQn, VAD_CNN_ISR); // Set CNN complete vector',
)
assert 'NVIC_SetPriority(CNN_IRQn, 5)' in c, 'NVIC_SetVector 那行没匹配上'

# vad_cnn_time 的定义
c = c.replace(
    'extern TaskHandle_t cnn_isr;',
    'volatile uint32_t vad_cnn_time;   /* 头文件里是 extern，这里给定义 */\n\n'
    'extern TaskHandle_t cnn_isr;',
)
assert 'volatile uint32_t vad_cnn_time;' in c

# 输出对齐现役 sen1：去掉左移，raw int8
# ⚠ 左移量不是固定值：sen1 是 `<< 5`，two_base 生成的是 `<< 4`。写死 `<< 5` 的字符串
#   替换会静默失效，留下 `<< 4`，于是 out_buf[0] = (0xf7<<4)=0x0F70，app 取 &0xff 得到
#   0x70 而不是 -9，margin 从 -15 变成 +112。必须用正则吃掉任意位数。
c = re.sub(r'\*out_buf\+\+ = \(int16_t\)\(\(val & 0xff\)\) << \d+;',
           '*out_buf++ = (val & 0xff);', c)
c = re.sub(r'\*out_buf\+\+ = \(int16_t\)\(\(\(val >> 8\) & 0xff\)\) << \d+;',
           '*out_buf++ = ((val >> 8) & 0xff);', c)
assert '<< ' not in c.split('int vad_cnn_unload')[1].split('return VAD_CNN_OK')[0], \
    'unload 里还有残留的左移，输出解码会错'

with open(os.path.join(DST, f'{PREFIX}.c'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

# ---------------- cnn.h ----------------
with open(os.path.join(SRC, 'cnn.h'), 'r', encoding='utf-8') as f:
    h = f.read()
h = rename_common(h)
h = h.replace('#ifndef __CNN_H__', f'#ifndef __{PREFIX.upper()}_H__')
h = h.replace('#define __CNN_H__', f'#define __{PREFIX.upper()}_H__')
h = h.replace('#endif // __CNN_H__', f'#endif // __{PREFIX.upper()}_H__')
h = h.replace('#include <stdint.h>\ntypedef int32_t q31_t;\ntypedef int16_t q15_t;',
              '#include <stdint.h>\n#include "model_common.h"')
h = re.sub(r'/\* Run software SoftMax on unloaded data \*/\nvoid softmax_q17p14_q15[^\n]*\n'
           r'/\* Shift the input[^\n]*\nvoid softmax_shift_q17p14_q15[^\n]*\n\n?', '', h)
with open(os.path.join(DST, f'{PREFIX}.h'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(h)

# ---------------- weights.h ----------------
with open(os.path.join(SRC, 'weights.h'), 'r', encoding='utf-8') as f:
    w = f.read()
with open(os.path.join(DST, f'{PREFIX}_weights.h'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(w)

print('done ->', DST)
for name in sorted(os.listdir(DST)):
    print(' ', name, os.path.getsize(os.path.join(DST, name)))
