/**
 * @file    app_tasks.c
 * @brief   sys_agent 的 9 个任务、同步对象和帧缓冲池。
 *
 * 本文件目前是**可编译可运行的空壳**：同步对象已建好，任务各自阻塞在
 * 自己的队列/通知上，往里填逻辑即可。每个任务都标了 TODO 和已知坑。
 *
 * 填的顺序建议：
 *   1) vTaskAudioCapture  → 先把 I2S + DMA 跑通，用 printf 验证数据在动
 *   2) vTaskPreprocess    → 折叠 + 量化，把 128x128 int8 打几行出来看
 *   3) vTaskSentinel      → 接 sen_cnn，先跑通 cnni 全流程
 *   4) vTaskGate          → 阈值 + 去抖动
 *   5) vTaskDeepInfer     → 接 kws_cnn
 *   6) vTaskReport        → softmax + 类名
 *   7) vTaskUartLink      → 先只发不收
 *   8) vTaskCache / vTaskMonitor / WDT
 */

#include <stdio.h>
#include <string.h>

#include "mxc.h"
#include "app_config.h"
#include "app_tasks.h"

/* 两个改名后的模型（见 tools/namespace_models.py） */
#include "sen_cnn.h"
#include "kws_cnn.h"

/* ══════════════════════════════════════════════════════════════
 * 零、模型侧必须由应用提供的符号
 *
 *   ai8xize 生成的代码里 `sen_cnn_time` / `kws_cnn_time` 只有
 *   `extern` 声明，**定义必须由应用补**，否则链接报 undefined reference。
 *   原独立工程是在各自 main.c 里定义的。
 * ══════════════════════════════════════════════════════════════ */
volatile uint32_t sen_cnn_time;
volatile uint32_t kws_cnn_time;

/* ══════════════════════════════════════════════════════════════
 * 一、全局对象
 * ══════════════════════════════════════════════════════════════ */

QueueHandle_t g_q_frame;
QueueHandle_t g_q_gate;
QueueHandle_t g_q_result;
QueueHandle_t g_q_cmd;
QueueHandle_t g_q_frame_free;

SemaphoreHandle_t g_sem_audio;
SemaphoreHandle_t g_mtx_cnn;

TaskHandle_t g_task_deep;
static TaskHandle_t fifo_task_sentinel;
/** 帧缓冲池：静态分配，16 KB x APP_FRAME_POOL。
 *  ⚠ 千万别用 pvPortMalloc 取（RTOS 堆只有 24 KB，放不下两块 16 KB）。 */
app_frame_t g_frame_pool[APP_FRAME_POOL];

/** 结果环形缓冲：只由 vTaskReport 写，其余任务只读，故无需加锁。 */
#define APP_RESULT_LOG_LEN 32
static app_result_t g_result_log[APP_RESULT_LOG_LEN];
static volatile uint32_t g_result_log_head; /* 下一个写入位置 */
static volatile uint32_t g_result_log_count; /* 累计写入总数 */
#define I2S_RX_BUFFER_SIZE 256
/* ══════════════════════════════════════════════════════════════
 * 一之二、模型接口表
 *
 *   把 sen_cnn_* / kws_cnn_* 两套同形状的 API 统一成一张表：
 *     - 上层不用写 if-else，换模型只改表
 *     - 表里对两边符号的引用，能阻止 --gc-sections 把某个模型整块回收，
 *       从而在链接期暴露出任何符号冲突（这是"两模型共存"的证明）
 * ══════════════════════════════════════════════════════════════ */

const app_model_t g_model_sen = {
    .name = "sentinel",
    .enable = sen_cnn_enable,
    .init = sen_cnn_init,
    .load_weights = sen_cnn_load_weights,
    .load_bias = sen_cnn_load_bias,
    .configure = sen_cnn_configure,
    .start = sen_cnn_start,
    .stop = sen_cnn_stop,
    .unload = sen_cnn_unload,
    .time_us = &sen_cnn_time,
    .out_words = APP_SEN_OUT_WORDS,
};

const app_model_t g_model_kws = {
    .name = "kws26",
    .enable = kws_cnn_enable,
    .init = kws_cnn_init,
    .load_weights = kws_cnn_load_weights,
    .load_bias = kws_cnn_load_bias,
    .configure = kws_cnn_configure,
    .start = kws_cnn_start,
    .stop = kws_cnn_stop,
    .unload = kws_cnn_unload,
    .time_us = &kws_cnn_time,
    .out_words = APP_KWS_OUT_WORDS,
};

/* 注册表：main() 会遍历打印，同时保证两个模型都进固件 */
const app_model_t *const g_models[] = { &g_model_sen, &g_model_kws };
const int g_model_count = (int)(sizeof(g_models) / sizeof(g_models[0]));

/** 全局统计，debug 用 */
static uint32_t g_stat_frames; /* 已处理帧数 */
static uint32_t g_stat_drops; /* 因池空丢掉的帧数 */
static uint32_t g_stat_anomaly; /* 判异常次数 */

/* ══════════════════════════════════════════════════════════════
 * 二、初始化
 * ══════════════════════════════════════════════════════════════ */

int app_sync_init(void)
{
    int i;

    /* 前处理 -> 哨兵：队列深度 1 就够（CNN 只要 39 µs，不会积压） */
    g_q_frame = xQueueCreate(1, sizeof(app_frame_t *));
    if (!g_q_frame) return 1;

    g_q_gate = xQueueCreate(2, sizeof(app_gate_t));
    if (!g_q_gate) return 2;

    g_q_result = xQueueCreate(4, sizeof(app_result_t));
    if (!g_q_result) return 3;

    g_q_cmd = xQueueCreate(4, sizeof(app_cmd_t));
    if (!g_q_cmd) return 4;

    /* 空闲帧池：队列当链表用，比计数信号量直观 */
    g_q_frame_free = xQueueCreate(APP_FRAME_POOL, sizeof(app_frame_t *));
    if (!g_q_frame_free) return 5;

    g_sem_audio = xSemaphoreCreateBinary();
    if (!g_sem_audio) return 6;

    g_mtx_cnn = xSemaphoreCreateMutex();
    if (!g_mtx_cnn) return 7;

    /* 把所有帧块挂进空闲池 */
    for (i = 0; i < APP_FRAME_POOL; i++) {
        app_frame_t *f = &g_frame_pool[i];
        memset(f, 0, sizeof(*f));
        if (xQueueSend(g_q_frame_free, &f, 0) != pdPASS) return 8;
    }

    g_result_log_head = 0;
    g_result_log_count = 0;
    return 0;
}

int app_tasks_create(void)
{
    /* 优先级 / 栈深见 app_config.h。
     * ⚠ 栈深单位是**字**（4 B），不是字节。 */
    if (xTaskCreate(vTaskAudioCapture_process, "audio", APP_STACK_AUDIO, NULL,
                    APP_PRIO_AUDIO, &fifo_task_sentinel) != pdPASS)
        return 1;
    if (xTaskCreate(vTaskSentinel, "sentinel", APP_STACK_SENTINEL, NULL,
                    APP_PRIO_SENTINEL, NULL) != pdPASS)
        return 3;
    if (xTaskCreate(vTaskGate, "gate", APP_STACK_GATE, NULL,
                    APP_PRIO_GATE, NULL) != pdPASS)
        return 4;
    /* 深层推理任务：句柄留着，靠任务通知按需唤醒 */
    if (xTaskCreate(vTaskDeepInfer, "deep", APP_STACK_DEEP, NULL,
                    APP_PRIO_DEEP, &g_task_deep) != pdPASS)
        return 5;
    if (xTaskCreate(vTaskReport, "report", APP_STACK_REPORT, NULL,
                    APP_PRIO_REPORT, NULL) != pdPASS)
        return 6;
    if (xTaskCreate(vTaskUartLink, "uart", APP_STACK_UART, NULL,
                    APP_PRIO_UART, NULL) != pdPASS)
        return 7;
    if (xTaskCreate(vTaskCache, "cache", APP_STACK_CACHE, NULL,
                    APP_PRIO_CACHE, NULL) != pdPASS)
        return 8;
    if (xTaskCreate(vTaskMonitor, "monitor", APP_STACK_MONITOR, NULL,
                    APP_PRIO_MONITOR, NULL) != pdPASS)
        return 9;

    return pdPASS;
}

/* ══════════════════════════════════════════════════════════════
 * 三、帧缓冲池
 * ══════════════════════════════════════════════════════════════ */

app_frame_t *app_frame_acquire(TickType_t ticks_to_wait)
{
    app_frame_t *f = NULL;
    if (xQueueReceive(g_q_frame_free, &f, ticks_to_wait) != pdPASS) {
        g_stat_drops++;
        return NULL;
    }
    return f;
}

void app_frame_release(app_frame_t *f)
{
    if (!f) return;
    /* 池满说明归还次数对不上（重复归还），队列深度就是池大小，不会溢出 */
    (void)xQueueSend(g_q_frame_free, &f, 0);
}

/* ══════════════════════════════════════════════════════════════
 * 三之二、结果环形缓冲的读接口
 *
 *   写者只有一个（vTaskReport），读者可以有多个，故无需加锁。
 * ══════════════════════════════════════════════════════════════ */

/** 取最近一条结果。返回 false 表示还没有任何结果。 */
bool app_result_log_latest(app_result_t *out)
{
    uint32_t i;
    if (!out || g_result_log_count == 0) return false;
    i = (g_result_log_head + APP_RESULT_LOG_LEN - 1) % APP_RESULT_LOG_LEN;
    *out = g_result_log[i];
    return true;
}

/** 已累计产生多少条结果（含被覆盖的）。 */
uint32_t app_result_log_total(void)
{
    return g_result_log_count;
}

/** 按时间顺序取第 idx 条（0 = 最老的一条仍在缓冲里的）。 */
bool app_result_log_get(uint32_t idx, app_result_t *out)
{
    uint32_t n = g_result_log_count < APP_RESULT_LOG_LEN ? g_result_log_count
                                                         : APP_RESULT_LOG_LEN;
    if (!out || idx >= n) return false;
    *out = g_result_log[(g_result_log_head + APP_RESULT_LOG_LEN - n + idx) %
                        APP_RESULT_LOG_LEN];
    return true;
}

/* ══════════════════════════════════════════════════════════════
 * 四、I2S DMA 回调（中断上下文）
 * ══════════════════════════════════════════════════════════════ */

void app_i2s_dma_callback(void)
{
    /* ⚠ 这是中断上下文：
     *    - 只能用 ...FromISR 版 API
     *    - 不要 printf
     *    - 用完必须 portYIELD_FROM_ISR，否则采集任务要等一个 tick 才醒
     */
    BaseType_t hpw = pdFALSE;
    xSemaphoreGiveFromISR(g_sem_audio, &hpw);
    portYIELD_FROM_ISR(hpw);
}

/* ══════════════════════════════════════════════════════════════
 * 四之二、FreeRTOS 钩子
 *
 *   FreeRTOSConfig.h 里打开了 configCHECK_FOR_STACK_OVERFLOW=2 和
 *   configUSE_MALLOC_FAILED_HOOK=1，**必须**提供这两个函数，否则链接报
 *   undefined reference。多任务应用最常见的两类崩溃就在这里。
 * ══════════════════════════════════════════════════════════════ */

/** 任务栈溢出：说明某个任务的栈开小了，回去加大 app_config.h 里的 APP_STACK_* */
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    printf("\n*** STACK OVERFLOW in task '%s' ***\n", pcTaskName ? pcTaskName : "?");
    printf("    -> 加大 app_config.h 里对应的 APP_STACK_* 值\n");
    taskDISABLE_INTERRUPTS();
    for (;;) {}
}

/** 堆耗尽：说明任务/队列开多了，或动了 configTOTAL_HEAP_SIZE */
void vApplicationMallocFailedHook(void)
{
    printf("\n*** MALLOC FAILED (heap %u B exhausted) ***\n",
           (unsigned)configTOTAL_HEAP_SIZE);
    printf("    -> 减任务/队列，或用 xTaskCreateStatic 静态分配，或加大堆\n");
    taskDISABLE_INTERRUPTS();
    for (;;) {}
}

/* ══════════════════════════════════════════════════════════════
 * 五、9 个任务
 * ══════════════════════════════════════════════════════════════ */

/* ── 1 音频采集 2 前处理：PCM -> int8 -> 折叠 128x128─────────────────────────────────────────────── */
volatile uint8_t i2s_flag = 0;
void i2s_isr(void)
{   
    BaseType_t higher_woken = pdFALSE;
    vTaskNotifyGiveFromISR(fifo_task_sentinel,&higher_woken);
    MXC_I2S_ClearFlags(MXC_F_I2S_INTFL_RX_THD_CH0);   
    portYIELD_FROM_ISR(higher_woken);  
}
void vTaskAudioCapture_process(void *pv)
{
    
    static uint32_t ring[256];   // 32-bit/样本！见 app_config.h
    int32_t err;
    mxc_i2s_req_t req;
#ifdef BOARD_FTHR_REVA
    if (max20303_init(MXC_I2C1) != E_NO_ERROR) {
        printf("Unable to initialize I2C interface to commonicate with PMIC!\n");
        while (1) {}
    }

    if (max20303_mic_power(1) != E_NO_ERROR) {
        printf("Unable to turn on microphone!\n");
        while (1) {}
    }

    MXC_Delay(MXC_DELAY_MSEC(200));

    printf("\nMicrophone enabled!\n");
#endif
    req.wordSize    = MXC_I2S_WSIZE_WORD;
    req.sampleSize  = MXC_I2S_SAMPLESIZE_THIRTYTWO; 
    req.bitsWord    = 32; 
    req.adjust      = MXC_I2S_ADJUST_LEFT;
    req.justify     = MXC_I2S_MSB_JUSTIFY;
    req.wsPolarity  = MXC_I2S_POL_NORMAL;
    req.channelMode = MXC_I2S_INTERNAL_SCK_WS_0;
    req.stereoMode  = MXC_I2S_MONO_LEFT_CH;   // 板载麦只出左声道
    req.bitOrder    = MXC_I2S_MSB_FIRST;
    req.clkdiv      = MXC_I2S_CalculateClockDiv(APP_SAMPLE_RATE, req.wordSize,
                                                  APP_I2S_EXT_CLK_HZ);
    req.rawData     = NULL;
    req.txData      = NULL;
    req.rxData      = ring;
    req.length = I2S_RX_BUFFER_SIZE;    
    if ((err = MXC_I2S_Init(&req)) != E_NO_ERROR) {
        printf("\nError in I2S_Init: %d\n", err);

        while (1) {}
    }
    MXC_NVIC_SetVector(I2S_IRQn, i2s_isr);
    NVIC_SetPriority(I2S_IRQn, 5); 
    NVIC_EnableIRQ(I2S_IRQn);
    MXC_I2S_SetRXThreshold(APP_I2S_RX_THRESHOLD);
    MXC_I2S_EnableInt(MXC_F_I2S_INTEN_RX_THD_CH0);  //之后切换为丢帧的触发源头
    MXC_I2S_RXEnable();
    while (1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);  //阻塞，等待数据
        uint32_t n = MXC_I2S->dmach0 >> MXC_F_I2S_DMACH0_RX_LVL_POS;

        if (xSemaphoreTake(g_sem_audio, portMAX_DELAY) != pdPASS) continue;

        /* TODO(2)：把 ring 里的 APP_FRAME_HOP 个新采样点交给前处理。
         *   最省事的做法：直接把 ring 指针放到一个全局变量里，
         *   然后 notify 前处理任务（避免拷贝 32 KB）。
         */

        app_frame_t *f = app_frame_acquire(0);
        if (!f) continue; /* 池空：本帧丢弃，计数已加 */

        /* TODO(3)：折叠 + 量化，**必须和训练时逐位一致**。
         *
         * 训练侧（tiny_sentinel.py 的 to_folded）：
         *     x = s / 32768.0                       // int16 -> float[-1,1]
         *     q = clip(round((x + 1) * 128), 0, 255) - 128   // -> [-128,127]
         *
         * 板上的 I2S 给的是 **32 位字**，有效数据在高 18 位（见 TODO(1)）。
         * 把它代进上式会**全部约掉**，只剩两次右移：
         *
         *     word(32bit)  --(>>14)-->  int16 s  --(>>8)-->  int8 q
         *     ⇒  q = (int8_t)((int32_t)word >> 22);
         *
         * 所以不需要浮点、不需要 clamp（移位天然落在 [-128,127]）。
         *
         *   for (i = 0; i < APP_RING_SAMPLES; i++) {
         *       int8_t q = (int8_t)((int32_t)ring[i] >> 22);
         *       f->data[(i % 128) * 128 + (i / 128)] = q;   // reshape(128,128).T
         *   }
         *
         * ⚠ 这个 >>22 的推导依赖"高 18 位"这个前提。换板子/换麦克风后
         *   必须重新确认移位量，否则整帧数据会错位。
         *
         * 💡 优化：CNN 输入内存（0x50400000 起，按 0x8000 分块）是**加速器自己的
         *    内存，不占 SRAM**。可以直接折叠写进去，连这 16 KB 帧缓冲都省掉，
         *    地址布局照抄 models/sen/sen_cnn.c 里各输入块的分配。
         *
         * 💡 更省内存：折叠的下标映射是确定的，可以在 I2S 回调里**边收边散写**，
         *    这样连 ring 都不用攒满 16384（见 app_config.h 的 APP_I2S_DMA_SAMPLES）。
         */

        f->seq = g_stat_frames++;
        f->t_ms = xTaskGetTickCount() * portTICK_PERIOD_MS;

        if (xQueueSend(g_q_frame, &f, 0) != pdPASS) {
            app_frame_release(f); /* 哨兵来不及收，丢帧 */
        }
    }
}

/* ── ──────────────────── */

/* ── 3 哨兵推理（CNN 加速器，实测 39 µs） ───────────────────── */
void vTaskSentinel(void *pv)
{
    (void)pv;
    uint32_t out[APP_SEN_OUT_WORDS];
    (void)out; /* TODO 里接上 sen_cnn_unload 后就不需要这行 */

    /* TODO(4)：开一次时钟即可，别每个任务都 enable/disable。
     *   cnn_enable() 会动 GCR 外设时钟，两个模型共用同一份硬件。 */
    /* sen_cnn_enable(MXC_S_GCR_PCLKDIV_CNNCLKSEL_PCLK,
     *                MXC_S_GCR_PCLKDIV_CNNCLKDIV_DIV1); */

    while (1) {
        app_frame_t *f = NULL;
        if (xQueueReceive(g_q_frame, &f, portMAX_DELAY) != pdPASS) continue;

        app_gate_t g = { .seq = f ? f->seq : 0 };

        /* ⚠ 拿 CNN 互斥量：加速器单实例，深层推理可能正在用 */
        if (xSemaphoreTake(g_mtx_cnn, portMAX_DELAY) == pdTRUE) {
            /* TODO(5)：跑哨兵推理
             *   sen_cnn_init();          // 状态机归位
             *   sen_cnn_load_weights();  // 10 KB 权重从 Flash 搬进加速器
             *   sen_cnn_load_bias();
             *   sen_cnn_configure();     // 每次换模型必须重配！
             *   load_cnn_input(f->data); // 折叠数据写进 0x50400000 区
             *   sen_cnn_start();
             *   while (sen_cnn_time == 0) { }   // 或等 CNN_IRQn
             *   sen_cnn_unload(out);
             */
            xSemaphoreGive(g_mtx_cnn);
        }

        /* TODO(6)：算异常概率。两条路可选：
         *   (a) 直接用 2 分类头（开箱即用，本次生成的就是这个）：
         *         int8_t l0 = (int8_t)(out[0] & 0xff);
         *         int8_t l1 = (int8_t)((out[0] >> 8) & 0xff);
         *         g.anomaly_prob = softmax2(l0, l1);
         *   (b) 16 维 embedding + 质心距离（更贴合原设计，但**需要改模型**）：
         *         要在 models/sen/sen_cnn.c 的 sen_cnn_unload() 里改成从
         *         layer 3 的 avg_pool 输出（16 个 int8 = 4 个 uint32）取数，
         *         而不是现在的 layer 4 二分类输出。
         */
        g.anomaly_prob = 0.0f;

        /* 用完立刻归还，门控只需要概率 */
        app_frame_release(f);
        (void)xQueueSend(g_q_gate, &g, 0);
    }
}

/* ── 4 门控决策 ─────────────────────────────────────────────── */
void vTaskGate(void *pv)
{
    (void)pv;
    uint32_t hit = 0; /* 连续判异常计数，去抖动用 */

    while (1) {
        app_gate_t g;
        if (xQueueReceive(g_q_gate, &g, portMAX_DELAY) != pdPASS) continue;

        if (g.anomaly_prob >= APP_GATE_THRESHOLD) {
            if (++hit >= APP_GATE_CONSECUTIVE) {
                hit = 0;
                g_stat_anomaly++;
                g.is_anomaly = true;
                /* TODO(7)：唤醒深层推理任务。
                 *   用任务通知最省内存，且天然支持"忙时不重复唤醒"：
                 *   xTaskNotifyGive(g_task_deep);   // 覆盖式，不会堆积
                 */
                if (g_task_deep) xTaskNotifyGive(g_task_deep);
            }
        } else {
            hit = 0;
        }
    }
}

/* ── 5 深层推理（CNN 加速器，实测 122 µs，按需唤醒） ─────────── */
void vTaskDeepInfer(void *pv)
{
    (void)pv;
    uint32_t out[APP_KWS_OUT_WORDS];

    while (1) {
        /* 阻塞等门控唤醒；pdTRUE = 取走并清零计数 */
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        if (xSemaphoreTake(g_mtx_cnn, portMAX_DELAY) == pdTRUE) {
            /* TODO(8)：跑 26 类口令识别，流程同哨兵但要换整套权重：
             *   kws_cnn_init();
             *   kws_cnn_load_weights();   // 100 KB，比哨兵大 10 倍
             *   kws_cnn_load_bias();
             *   kws_cnn_configure();      // 与哨兵的配置不同，必须重配
             *   kws_cnn_start();
             *   while (kws_cnn_time == 0) { }
             *   kws_cnn_unload(out);
             *
             * 💡 两个模型的权重不能同时驻留，每次切换都要重新 load+configure。
             *    总耗时 ≈ 39 + 122 µs + 搬运时间，仍然远小于一帧 1.024 s。
             */
            memset(out, 0, sizeof(out));
            xSemaphoreGive(g_mtx_cnn);
        }

        /* 把 26 个 int32 打分丢给结果任务（不要在这里做 softmax，占栈） */
        /* TODO(9)：xQueueSend 给 vTaskReport */
    }
}

/* ── 6 结果处理 ─────────────────────────────────────────────── */
void vTaskReport(void *pv)
{
    (void)pv;

    while (1) {
        /* TODO(10)：等深层推理的结果 → softmax → 取最大类 → 组包
         *   softmax_q17p14_q15(out, APP_KWS_CLASSES, probs);
         *
         * 然后：
         *   app_result_t r = { .class_id = best, .prob = p, ... };
         *   g_result_log[g_result_log_head] = r;     // 环形缓冲，单写者无需锁
         *   g_result_log_head = (g_result_log_head + 1) % APP_RESULT_LOG_LEN;
         *   g_result_log_count++;
         *   xQueueSend(g_q_result, &r, 0);           // 给串口任务
         *   printf("%s (%.2f)\n", kws_class_name(best), p);
         */

        vTaskDelay(pdMS_TO_TICKS(500)); /* 占位：别变成忙等 */
    }
}

/* ── 7 串口通讯（与 Jetson 双向） ───────────────────────────── */
void vTaskUartLink(void *pv)
{
    (void)pv;

    /* TODO(11)：初始化链路串口（和调试口分开，见 app_config.h）
     *   MXC_UART_Init(MXC_UART_GET_UART(APP_LINK_UART), APP_LINK_BAUD,
     *                 MXC_UART_APB_CLK);
     *
     * 收：用异步事务 + 任务通知，**照抄**
     *     02_rtos/MAX78000_FreeRTOSDemo/main.c 的 vCmdLineTask：
     *       - 注册 mxc_uart_req_t，callback 里 vTaskNotifyGiveFromISR
     *       - 必须在 UARTx_IRQHandler 里调 MXC_UART_AsyncHandler()
     *     收到的字节拼成 app_cmd_t 丢进 g_q_cmd。
     *
     * 发：xQueueReceive(g_q_result, ...) → 组帧 → MXC_UART_Write
     */

    while (1) {
        app_result_t r;
        if (xQueueReceive(g_q_result, &r, portMAX_DELAY) == pdPASS) {
            /* TODO(12)：把 r 编码成和 Jetson 约定的帧格式发出去 */
        }
    }
}

/* ── 8 缓存管理 ─────────────────────────────────────────────── */
void vTaskCache(void *pv)
{
    (void)pv;
    TickType_t last = xTaskGetTickCount();

    while (1) {
        /* TODO(13)：周期清理 / 统计。
         *   - 超过一定时长的旧结果丢弃
         *   - 打印 g_stat_frames / g_stat_drops / g_stat_anomaly
         *   - 必要时把结果落到 Flash（注意写寿命，别频繁写）
         */
        vTaskDelayUntil(&last, pdMS_TO_TICKS(10000));
    }
}

/* ── 9 监控（喂狗 + 栈水位，兜底） ─────────────────────────── */
void vTaskMonitor(void *pv)
{
    (void)pv;
    TickType_t last = xTaskGetTickCount();

    /* TODO(14)：确认所有任务都跑起来后再开看门狗，否则调试期会不停复位。
     *   MXC_WDT_Init(MXC_WDT0, MXC_WDT_WINDOWED);   // 见 03_api/periph/wdt.md
     */

    while (1) {
        /* TODO(15)：喂狗 */
        /* MXC_WDT_PetWatchdog(MXC_WDT0); */

        /* TODO(16)：栈够不够？这个函数返回**历史最小剩余量（字）**。
         * 任何任务剩余 < 约 32 字（128 B）就该加大栈。
         *   printf("stack high water: audio=%u preproc=%u deep=%u\n",
         *          uxTaskGetStackHighWaterMark(NULL), ...);
         */
        vTaskDelayUntil(&last, pdMS_TO_TICKS(APP_WDT_FEED_MS));
    }
}
