/**
 * @file    app_config.h
 * @brief   sys_agent MAX78000 应用的**集中配置**。
 *
 * 所有"要调的数"都放这里：引脚、缓冲、任务优先级/栈、阈值。
 * 改行为先改这个文件，别去散落到各任务里。
 *
 * ── 硬件资源账（照这个算，别超）────────────────────────────
 *   Flash 512 KB ｜ SRAM 128 KB(130,944 B) ｜ 双核共享 128 B
 *   实测两个模型工程各占：Flash 12.4% / 18.1%，SRAM 4.1%
 *   CNN 加速器有独立 442 KB 权重内存，**不占 SRAM**
 *
 * ── SRAM 预算（本文件的默认值）─────────────────────────────
 *   I2S DMA 小 ring  APP_I2S_DMA_SAMPLES x 4 B =  4 KB   ← 32-bit/样本！
 *   帧缓冲池         APP_FRAME_POOL x 16 KB    = 32 KB
 *   FreeRTOS 堆      configTOTAL_HEAP_SIZE     = 24 KB
 *   任务栈合计       (见下表)                   ≈  8 KB
 *   ────────────────────────────────────────────────
 *   小计                                        ≈ 68 KB
 *   + .data/.bss（模型权重等，实测约 5.5 KB）→ 约 74 KB / 128 KB
 *
 *   ⚠ 如果不做「边收边折叠散写」，而是让 DMA 一次收满 16384 点，
 *     光 ring 就要 16384 x 4 B = **64 KB**，再加帧池 32 KB = 96 KB，
 *     基本没余量了。所以推荐小 ring + 任务里散写（见 app_tasks.c TODO(3)）。
 */

#ifndef APP_CONFIG_H_
#define APP_CONFIG_H_

#include <stdint.h>

/* ══════════════════════════════════════════════════════════════
 * 一、音频前处理
 * ══════════════════════════════════════════════════════════════ */

#define APP_SAMPLE_RATE 16000 /* 麦克风采样率 Hz */

/** 一帧需要的采样点数（= 折叠张量元素数）。
 *  ⚠ 必须等于 APP_FOLD_DIM * APP_FOLD_DIM，否则折叠出来的张量不完整。 */
#define APP_RING_SAMPLES 16384

/** ⚠⚠ I2S 是 **32 位字**，不是 16 位！
 *
 *  板载麦克风的数据占 32 位字的**高 18 位**（官方 kws20_demo 注释原话：
 *  "The actual value is 18 MSB of 32-bit word"），所以：
 *
 *      req.bitsWord   = 32;
 *      req.sampleSize = MXC_I2S_SAMPLESIZE_THIRTYTWO;
 *      int16_t s      = (int16_t)((int32_t)word >> 14);
 *
 *  推论：**DMA 缓冲必须是 uint32_t**，一帧 16384 点 = 64 KB，占半个 SRAM。
 *  所以不要一次 DMA 收满一帧，而是用下面这个小 ring + 半满/全满中断，
 *  在任务里「边收边折叠散写」到帧缓冲（见 app_tasks.c 的 TODO(3)）。
 */
#define APP_I2S_DMA_SAMPLES 1024 /* 4 KB (uint32_t)，半满 = 512 点 = 32 ms */

/** I2S 外部主时钟。板载 12.288 MHz 晶振（EVKIT 需把 J20 跳到 INT）。 */
#define APP_I2S_EXT_CLK_HZ 12288000

/** 麦克风数据在 32 位字里的有效起始位：右移这么多次得到 int16。
 *  换板子/换麦克风后**必须重新确认**，否则整帧数据错位。 */
#define APP_I2S_SHIFT_TO_S16 14

/** 由 32 位 I2S 字直接得到 CNN 的 int8 输入。
 *  推导：q = round((s/32768 + 1)*128) - 128 = s >> 8 = (word >> 14) >> 8
 *  所以两次右移可以合并成一次 22 位右移，且天然落在 [-128,127]，无需 clamp。 */
#define APP_I2S_WORD_TO_INT8(w) ((int8_t)((int32_t)(w) >> 22))

/** 折叠后张量边长：128 x 128 = 16384 点，正好是 CNN 输入尺寸。 */
#define APP_FOLD_DIM 128

/** 折叠后一帧的字节数（int8 量化后）。 */
#define APP_FRAME_BYTES (APP_FOLD_DIM * APP_FOLD_DIM) /* 16384 B = 16 KB */

/** 帧缓冲池大小（前后级解耦用）。每块 16 KB。
 *  1 = 最省内存但前后级必须严格串行；2 = 可流水；3 = 更宽松但 SRAM 吃紧。 */
#define APP_FRAME_POOL 2

/** 送检节奏：每收满多少个采样点送一帧。
 *  = APP_RING_SAMPLES 则每 1.024 s 一帧（最省 CPU）；
 *  = 8192 则 512 ms 一帧（滑窗，延迟减半，CPU 翻倍）。 */
#define APP_FRAME_HOP APP_RING_SAMPLES

/* ══════════════════════════════════════════════════════════════
 * 二、CNN 模型参数
 * ══════════════════════════════════════════════════════════════ */

/** 哨兵：2 分类（正常/异常），输出压成 1 个 uint32（含 2 个 int8）。
 *  实测 3,894 周期 ≈ 39 µs @100 MHz。 */
#define APP_SEN_OUT_WORDS 1

/** 中文口令：26 类，输出 26 个 uint32。
 *  实测 12,204 周期 ≈ 122 µs @100 MHz。 */
#define APP_KWS_OUT_WORDS 26
#define APP_KWS_CLASSES 26

/** 门控阈值：占位值，**必须用 calibrate 流程在你的实际环境重算**。
 *  判据：哨兵输出 softmax 后 异常类概率 > APP_GATE_THRESHOLD 即唤醒深层模型。
 *  若改用 16 维 embedding 质心距离，见 app_tasks.c 的 TODO。 */
#define APP_GATE_THRESHOLD 0.50f

/** 去抖动：连续 N 帧判异常才真正唤醒深层模型（防单帧误触发）。 */
#define APP_GATE_CONSECUTIVE 2

/* ══════════════════════════════════════════════════════════════
 * 三、任务优先级与栈
 *   优先级见 FreeRTOSConfig.h 的 configMAX_PRIORITIES（=8，可用 0..7）
 *   栈深单位是**字**（StackType_t = uint32_t），1 字 = 4 B
 * ══════════════════════════════════════════════════════════════ */

#define APP_PRIO_AUDIO 7 /* 硬实时：I2S DMA，绝不能被拖 */
#define APP_PRIO_PREPROC 6 /* 前处理：折叠量化，纯 CPU */
#define APP_PRIO_SENTINEL 6 /* 哨兵推理：用 CNN，39 µs */
#define APP_PRIO_GATE 5 /* 门控决策：纯 CPU，很短 */
#define APP_PRIO_DEEP 4 /* 深层推理：按需唤醒，122 µs */
#define APP_PRIO_REPORT 4 /* 结果处理：softmax + 组包 */
#define APP_PRIO_UART 3 /* 串口收发：可被上面抢占 */
#define APP_PRIO_CACHE 2 /* 缓存管理：低优先级周期活 */
#define APP_PRIO_MONITOR 1 /* 看门狗喂狗 / 状态监控 */

#define APP_STACK_AUDIO 512 /* 2 KB */
#define APP_STACK_PREPROC 384 /* 1.5 KB */
#define APP_STACK_SENTINEL 384
#define APP_STACK_GATE 256 /* 1 KB */
#define APP_STACK_DEEP 512 /* 2 KB：26 类 softmax 要些空间 */
#define APP_STACK_REPORT 384
#define APP_STACK_UART 512 /* 2 KB：收发缓冲大 */
#define APP_STACK_CACHE 256
#define APP_STACK_MONITOR 256

/* ══════════════════════════════════════════════════════════════
 * 四、串口（调试口 + 与 Jetson 通讯）
 * ══════════════════════════════════════════════════════════════ */

#define APP_CONSOLE_UART 0 /* 调试打印用 */
#define APP_CONSOLE_BAUD 115200

#define APP_LINK_UART 1 /* 与 Jetson 的双向链路 */
#define APP_LINK_BAUD 921600
#define APP_LINK_RX_BUF 256
#define APP_LINK_TX_BUF 256

/* ══════════════════════════════════════════════════════════════
 * 五、I2S 麦克风
 *   板载麦克风只出左声道；FTHR 板需要先给麦克风上电（PMIC max20303）
 * ══════════════════════════════════════════════════════════════ */

#define APP_I2S_STEREO_MONO 1 /* 1 = 只取左声道 */
#define APP_I2S_RX_THRESHOLD 4 /* FIFO 阈值，到就触发 DMA */

/* ══════════════════════════════════════════════════════════════
 * 六、低功耗 / 唤醒
 * ══════════════════════════════════════════════════════════════ */

/** tickless idle：默认关闭。
 *  打开前必须先实现 vPortSuppressTicksAndSleep（WUT 版），
 *  照抄 ../../02_rtos/MAX78000_FreeRTOSDemo/freertos_tickless.c，
 *  并重写 freertos_permit_tickless()：I2S/CNN 忙时返回 E_BUSY。 */
#define APP_USE_TICKLESS_IDLE 0

/** 空转多久没动静就进低功耗（ms） */
#define APP_IDLE_SLEEP_MS 1000

/* ══════════════════════════════════════════════════════════════
 * 七、看门狗
 * ══════════════════════════════════════════════════════════════ */

#define APP_WDT_TIMEOUT_MS 4000 /* 喂狗任务周期须显著小于此值 */
#define APP_WDT_FEED_MS 1000

/* ══════════════════════════════════════════════════════════════
 * 八、编译期调试开关
 * ══════════════════════════════════════════════════════════════ */

/** 打开后两个模型都会用 MXC_TMR_SW_* 统计推理周期数，结果存
 *  sen_cnn_time / kws_cnn_time（单位 µs）。需要先占用一个 TMR。 */
/* #define CNN_INFERENCE_TIMER  MXC_TMR2 */

/** 1 = 每个任务进出打时间戳到调试串口（会显著拖慢，仅调试用） */
#define APP_TRACE_TASKS 0

#endif /* APP_CONFIG_H_ */
