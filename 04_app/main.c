/**
 * @file    main.c
 * @brief   sys_agent MAX78000 应用入口。
 *
 * ⚠ 本文件只放 include 和 main() 本体。
 *   9 个任务的具体调度、参数、逻辑全在 app_tasks.c / app_config.h，
 *   这里只负责「上电 → 初始化 → 交棒给调度器」。
 */

#include <stdio.h>

#include "mxc.h" /* 总入口：拉通所有外设 + CMSIS + SEC()/MSEC() 宏 */
#include "app_config.h"
#include "app_tasks.h"

#include "sen_cnn.h" /* 哨兵模型（改名后，见 tools/namespace_models.py） */
#include "kws_cnn.h" /* 中文口令模型（同上） */

int main(void)
{
    int rc, i;

    /* ── 1. 开机基线：开指令缓存 + 切到 100 MHz ──────────────
     * ⚠ 上电默认是 ISO 60 MHz，不切的话所有周期数都要按 60 MHz 重算。 */
    MXC_ICC_Enable(MXC_ICC0);
    MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO);
    SystemCoreClockUpdate();

    /* 留 2 秒，方便调试器在初始化前挂上去 */
    MXC_Delay(SEC(2));

    printf("\n=== sys_agent MAX78000 ===\n");
    printf("SystemCoreClock = %u Hz\n", (unsigned)SystemCoreClock);
    printf("FreeRTOS kernel = %s\n", tskKERNEL_VERSION_NUMBER);
    /* 内存账：I2S 样本是 32 位（板载麦的有效数据在高 18 位），别按 16 位算 */
    printf("SRAM budget: i2s ring %u B (uint32), frame pool %u B, RTOS heap %u B\n",
           (unsigned)(APP_I2S_DMA_SAMPLES * sizeof(uint32_t)),
           (unsigned)(APP_FRAME_POOL * sizeof(app_frame_t)),
           (unsigned)(configTOTAL_HEAP_SIZE));

    /* 列出编进固件的模型 —— 两个模型共存且不冲突的运行时确认 */
    for (i = 0; i < g_model_count; i++) {
        printf("model[%d] = %-8s (%u out words)\n", i, g_models[i]->name,
               (unsigned)g_models[i]->out_words);
    }

    /* ── 2. CNN 加速器上电 ────────────────────────────────────
     * 两个模型共用同一份硬件，**只在这里开一次**，之后靠各自的
     * load_weights / configure 切换模型。 */
    sen_cnn_enable(MXC_S_GCR_PCLKDIV_CNNCLKSEL_PCLK, MXC_S_GCR_PCLKDIV_CNNCLKDIV_DIV1);

    /* ── 3. 创建同步对象（队列 / 信号量 / 互斥量 / 帧缓冲池）── */
    rc = app_sync_init();
    if (rc == 0) {
        /* ── 4. 创建 9 个任务 ──────────────────────────────── */
        rc = (app_tasks_create() == pdPASS) ? 0 : -1;
    }

    /* ── 5. 启动调度器（正常不返回）──────────────────────── */
    if (rc == 0) {
        printf("Starting scheduler.\n");
        vTaskStartScheduler();
        rc = -1; /* 走到这说明堆不够，调度器没起来 */
    }

    /* ── 6. 只有出错才会到这里 ───────────────────────────── */
    printf("ERROR: startup failed (rc=%d)\n", rc);
    for (;;) {
        __NOP();
    }
}
