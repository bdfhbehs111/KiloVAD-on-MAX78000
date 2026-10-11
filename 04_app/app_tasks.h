/**
 * @file    app_tasks.h
 * @brief   9 个任务的对外接口、共享数据结构和同步对象。
 *
 * main.c 只 include 这个头文件，调用 app_sync_init() / app_tasks_create()，
 * 然后 vTaskStartScheduler()。任务内部细节看 app_tasks.c。
 */

#ifndef APP_TASKS_H_
#define APP_TASKS_H_

#include <stdint.h>
#include <stdbool.h>
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#include "app_config.h"

/* ══════════════════════════════════════════════════════════════
 * 一、共享数据结构
 * ══════════════════════════════════════════════════════════════ */

/** 一帧折叠后的量化音频（送 CNN 的输入）。
 *  16 KB，从帧缓冲池里借，用完必须归还（app_frame_release）。 */
typedef struct {
    int8_t data[APP_FRAME_BYTES]; /* 折叠 128x128，值域 [-128,127] */
    uint32_t seq; /* 帧序号，递增，用于丢帧检测 */
    uint32_t t_ms; /* 采集时刻（tick 换算） */
} app_frame_t;

/** 哨兵门控结果 */
typedef struct {
    float anomaly_prob; /* 异常概率 [0,1] */
    bool is_anomaly; /* 去抖动后的最终判定 */
    uint32_t seq;
} app_gate_t;

/** 最终结果（送串口 / 上报 Jetson） */
typedef struct {
    uint16_t class_id; /* 0..APP_KWS_CLASSES-1，或哨兵的二分类 */
    float prob; /* 置信度 [0,1] */
    uint32_t seq;
    uint32_t t_ms;
} app_result_t;

/** Jetson 下发的命令 */
typedef enum {
    APP_CMD_NONE = 0,
    APP_CMD_SET_THRESHOLD, /* data.f 有效：改门控阈值 */
    APP_CMD_RESET_CENTROID, /* 触发重算质心/基线 */
    APP_CMD_SLEEP, /* 主动进低功耗 */
} app_cmd_id_t;

typedef struct {
    app_cmd_id_t id;
    float f;
} app_cmd_t;

/* ══════════════════════════════════════════════════════════════
 * 二、共享同步对象（在 app_tasks.c 里定义并创建）
 *
 *   数据流：
 *     I2S DMA ISR ──give g_sem_audio──> [1 采集]
 *        [1 采集] ──g_q_frame──> [2 前处理] ──g_q_frame──> [3 哨兵]
 *        [3 哨兵] ──g_q_gate──> [4 门控]
 *            ├─ 正常 ──> 丢弃
 *            └─ 异常 ──notify g_task_deep──> [5 深层]
 *        [5 深层] ──write g_result_log──> [6 结果] ──g_q_result──> [7 串口]
 *     [7 串口] ──g_q_cmd──> 各任务
 *     [8 缓存] 周期清理 g_result_log
 *     [9 监控] 喂狗 + 栈水位
 *
 *   ⚠ g_mtx_cnn 必不可少：CNN 加速器是**单实例硬件**，
 *     哨兵和深层推理不能同时用，必须串行化。
 * ══════════════════════════════════════════════════════════════ */

extern QueueHandle_t g_q_frame; /* app_frame_t* : 前处理 -> 哨兵 */
extern QueueHandle_t g_q_gate; /* app_gate_t   : 哨兵 -> 门控 */
extern QueueHandle_t g_q_result; /* app_result_t : 结果 -> 串口 */
extern QueueHandle_t g_q_cmd; /* app_cmd_t    : 串口 -> 各任务 */
extern QueueHandle_t g_q_frame_free; /* app_frame_t* : 空闲帧池（队列当链表用） */

extern SemaphoreHandle_t g_sem_audio; /* I2S DMA ISR -> 采集任务 */
extern SemaphoreHandle_t g_mtx_cnn; /* CNN 加速器互斥 */

extern TaskHandle_t g_task_deep; /* 深层推理任务句柄（按需唤醒） */

/** 帧缓冲池本体（静态分配，**不要**从 24 KB 的 RTOS 堆里再切 16 KB） */
extern app_frame_t g_frame_pool[APP_FRAME_POOL];

/* ══════════════════════════════════════════════════════════════
 * 二之二、模型接口表
 *
 *   两个模型被 ai8xize 生成的 API 形状完全一样，只是名字不同
 *   （sen_* / kws_*）。用一张表把它们统一起来，上层就不必写 if-else，
 *   换模型只改表。
 *
 *   ⚠ 这张表还有第二个作用：**它是"两个模型能共存"的编译期证明**。
 *     MSDK 编译带 --gc-sections，没有被引用的函数会被链接器回收。
 *     表里对两边符号的引用会让两个模型都真正进入最终固件，
 *     从而暴露任何符号冲突。
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    const char *name;
    int (*enable)(uint32_t clock_source, uint32_t clock_divider);
    int (*init)(void);
    int (*load_weights)(void);
    int (*load_bias)(void);
    int (*configure)(void);
    int (*start)(void);
    int (*stop)(void);
    int (*unload)(uint32_t *out_buf);
    volatile uint32_t *time_us; /* 推理耗时（需开 CNN_INFERENCE_TIMER） */
    uint16_t out_words; /* 输出占几个 uint32 */
} app_model_t;

extern const app_model_t g_model_sen; /* 极简哨兵：2 分类 */
extern const app_model_t g_model_kws; /* 中文口令：26 类 */

/** 模型注册表。main() 启动时会遍历它打印，既方便确认固件里到底带了哪些模型，
 *  也保证两个模型都不会被 --gc-sections 当死代码回收。 */
extern const app_model_t *const g_models[];
extern const int g_model_count;

/* ══════════════════════════════════════════════════════════════
 * 三、初始化（main.c 调用）
 * ══════════════════════════════════════════════════════════════ */

/** 创建所有队列 / 信号量 / 互斥量。返回 0 成功，非 0 = 失败对象编号。 */
int app_sync_init(void);

/** 创建 9 个任务。返回 pdPASS 成功；否则为失败任务的序号。 */
int app_tasks_create(void);

/* ══════════════════════════════════════════════════════════════
 * 四、任务（实现在 app_tasks.c，骨架 + TODO）
 * ══════════════════════════════════════════════════════════════ */

void vTaskAudioCapture_process(); /* 1 音频采集（I2S + DMA）2 前处理（量化 + 折叠 128x128） */
void vTaskSentinel(void *pv); /* 3 哨兵推理（sen_cnn, 39 µs） */
void vTaskGate(void *pv); /* 4 门控决策（阈值 + 去抖动） */
void vTaskDeepInfer(void *pv); /* 5 深层推理（kws_cnn, 122 µs，按需） */
void vTaskReport(void *pv); /* 6 结果处理（softmax → 组包） */
void vTaskUartLink(void *pv); /* 7 串口通讯（与 Jetson 双向） */
void vTaskCache(void *pv); /* 8 缓存管理（结果环形缓冲 + 清理） */
void vTaskMonitor(void *pv); /* 9 监控（喂狗 + 栈水位 + 状态，兜底） */

/* ══════════════════════════════════════════════════════════════
 * 五、给中断 / 跨任务用的辅助函数
 * ══════════════════════════════════════════════════════════════ */

/** I2S DMA 完成回调（在 **中断上下文** 里被调用）。
 *  ⚠ 只允许用 ...FromISR 版 API。 */
void app_i2s_dma_callback(void);

/** 取一帧空闲缓冲；池空则最多等 ticks_to_wait。返回 NULL 表示超时。 */
app_frame_t *app_frame_acquire(TickType_t ticks_to_wait);

/** 归还一帧缓冲（任务上下文）。 */
void app_frame_release(app_frame_t *f);

/** 取最近一条结果。返回 false 表示还没有任何结果。 */
bool app_result_log_latest(app_result_t *out);

/** 已累计产生多少条结果（含被环形缓冲覆盖掉的）。 */
uint32_t app_result_log_total(void);

/** 按时间顺序取第 idx 条（0 = 缓冲里最老的一条）。 */
bool app_result_log_get(uint32_t idx, app_result_t *out);

#endif /* APP_TASKS_H_ */
