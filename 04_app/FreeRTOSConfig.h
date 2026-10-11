/**
 * @file    FreeRTOSConfig.h
 * @brief   sys_agent 应用的 FreeRTOS 配置。
 *
 * 基线来自官方范例 02_rtos/MAX78000_FreeRTOSDemo/FreeRTOSConfig.h，
 * 改动处都标了「★ 本项目改动」，原因见 02_rtos/README.md 第四节。
 *
 * 内核：FreeRTOS V10.5.1，端口：GCC/ARM_CM4F（MSDK 构建只支持 M4F 核）
 */

#ifndef FREERTOS_CONFIG_H_
#define FREERTOS_CONFIG_H_

#include <stdint.h>
#include <stdio.h>
#include "max78000.h"
#include "app_config.h"

/*-----------------------------------------------------------
 * 调度相关
 *----------------------------------------------------------*/

/* 主频。⚠ 上电默认 ISO 60 MHz，main() 里显式选 IPO 后才是 100 MHz。
 *   FreeRTOS 在 vTaskStartScheduler 前读这个值算 SysTick 重载，
 *   所以必须与实际时钟一致 —— 两个模型工程都验证过 100 MHz 可用。 */
#define configCPU_CLOCK_HZ ((uint32_t)IPO_FREQ)

/* 1 ms 一个 tick。
 * ⚠ 16 kHz 采样下 1 tick = 16 个采样点。若前处理要按采样点粒度调度，
 *   要么提高 tick 频率（1000 -> 2000），要么靠 I2S DMA 中断驱动。 */
#define configTICK_RATE_HZ ((TickType_t)1000)

/* tickless idle 用时基（ERTCO 32.768 kHz）*/
#define configRTC_TICK_RATE_HZ (32768)

/* ★ 本项目改动：tickless 默认关闭。
 *   打开前必须先实现 vPortSuppressTicksAndSleep（WUT 版）并重写
 *   freertos_permit_tickless()，做法照抄：
 *       02_rtos/MAX78000_FreeRTOSDemo/freertos_tickless.c
 *   没实现就打开会导致传输中被睡眠打断，数据错乱。 */
#if APP_USE_TICKLESS_IDLE
#define configUSE_TICKLESS_IDLE 1
void vPreSleepProcessing(uint32_t *expectedIdleTime);
void vPostSleepProcessing(uint32_t expectedIdleTime);
#define configPRE_SLEEP_PROCESSING(idletime) vPreSleepProcessing(&idletime);
#define configPOST_SLEEP_PROCESSING(idletime) vPostSleepProcessing(idletime);
#endif

/* ★ 本项目改动：8 个优先级档（默认 5 不够 9 个任务分层）。
 *   可用优先级取值 0 .. configMAX_PRIORITIES-1 */
#define configMAX_PRIORITIES 8
#define configUSE_PREEMPTION 1
#define configUSE_IDLE_HOOK 0
#define configUSE_TICK_HOOK 0
#define configUSE_CO_ROUTINES 0
#define configUSE_16_BIT_TICKS 0
#define configUSE_MUTEXES 1
#define configUSE_RECURSIVE_MUTEXES 0
#define configUSE_COUNTING_SEMAPHORES 1
#define configUSE_TASK_NOTIFICATIONS 1
#define configUSE_TIME_SLICING 1

/*-----------------------------------------------------------
 * 内存
 *----------------------------------------------------------*/

/* ★ 本项目改动：24 KB。
 *   音频环形缓冲(32 KB)和帧缓冲池(2x16 KB)都是**静态全局数组**，
 *   不从这里出（否则 16 KB x 2 直接吃光）。这里只管任务栈 + 队列。
 *   估算：9 个任务栈合计约 8 KB + 队列约 0.2 KB -> 24 KB 余量充足。 */
#define configTOTAL_HEAP_SIZE ((size_t)(24 * 1024))

/* 空闲任务栈。单位是**字**（4 B），128 字 = 512 B */
#define configMINIMAL_STACK_SIZE ((uint16_t)128)

#define configSUPPORT_STATIC_ALLOCATION 0
#define configSUPPORT_DYNAMIC_ALLOCATION 1

/*-----------------------------------------------------------
 * 钩子（★ 本项目改动：都打开，新手期非常有用）
 *----------------------------------------------------------*/

/* 1 = 只查栈指针越界；2 = 再填 0xA5 图案查踩栈（更慢但更准）。
 * 需要实现 vApplicationStackOverflowHook()（在 app_tasks.c）。 */
#define configCHECK_FOR_STACK_OVERFLOW 2

/* 堆耗尽时回调，需要实现 vApplicationMallocFailedHook()（在 app_tasks.c）。
 * 多任务应用最容易在这里翻车，务必打开。 */
#define configUSE_MALLOC_FAILED_HOOK 1

/*-----------------------------------------------------------
 * 运行统计
 *----------------------------------------------------------*/

#define configUSE_TRACE_FACILITY 1
#define configUSE_STATS_FORMATTING_FUNCTIONS 1

/*★ 运行统计需要一个高频定时器（分辨率要 > 10x tick）。
 *  打开前先在 main 或 monitor 任务里配置好 TMR，
 *  且注意 TMR0 在低功耗模式下可能不准（见 02_rtos/README.md）。
 *  参考 02_rtos/MAX78000_FreeRTOSDemo/FreeRTOS_Debug.c */
/* #define configGENERATE_RUN_TIME_STATS 1 */
/* #define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS() ConfigTimerForStats()
 * #define portGET_RUN_TIME_COUNTER_VALUE()         GetTimerForStats() */

/*-----------------------------------------------------------
 * API 裁剪：用到什么开什么，省 Flash
 *----------------------------------------------------------*/

#define INCLUDE_vTaskPrioritySet 1 /* ★ 改动：动态调优先级 */
#define INCLUDE_uxTaskPriorityGet 1 /* ★ 改动：监控用 */
#define INCLUDE_vTaskDelete 1 /* ★ 改动：按需销毁任务 */
#define INCLUDE_vTaskSuspend 1
#define INCLUDE_vTaskDelayUntil 1 /* 周期任务防漂移，必须开 */
#define INCLUDE_vTaskDelay 1
#define INCLUDE_xTaskGetSchedulerState 1
#define INCLUDE_uxTaskGetStackHighWaterMark 1 /* ★ 查栈水位，调试必备 */
#define INCLUDE_xTaskGetCurrentTaskHandle 1
#define INCLUDE_xTaskGetIdleTaskHandle 0

/*-----------------------------------------------------------
 * 中断优先级（MAX78000 只实现高 3 位）
 *
 * ⚠ 铁律：任何要调用 FreeRTOS API 的 ISR，
 *   其 NVIC 优先级**数值**必须 >= configMAX_SYSCALL_INTERRUPT_PRIORITY。
 *   数值越大 = 优先级越低。设成 0~4 的 ISR 一调 API 就会 assert 挂掉。
 *----------------------------------------------------------*/

#define configPRIO_BITS __NVIC_PRIO_BITS /* = 3 */

#define configKERNEL_INTERRUPT_PRIORITY ((unsigned char)7 << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY ((unsigned char)5 << (8 - configPRIO_BITS))

/* 把 FreeRTOS 的 handler 名对到 CMSIS 的弱符号上 */
#define vPortSVCHandler SVC_Handler
#define xPortPendSVHandler PendSV_Handler
#define xPortSysTickHandler SysTick_Handler

/*-----------------------------------------------------------
 * 调试
 *----------------------------------------------------------*/

/* 断言失败就打印 + 停住，别静默死循环 —— 多任务下静默死机极难查 */
#define configASSERT(x)                                    \
    if ((x) == 0) {                                        \
        printf("ASSERT FAILED: %s:%d\n", __FILE__, __LINE__); \
        taskDISABLE_INTERRUPTS();                          \
        for (;;) {}                                        \
    }

#define configQUEUE_REGISTRY_SIZE 8

/* FreeRTOS+CLI 需要这个尺寸定义，本项目不用 CLI，给个最小值即可 */
#define configCOMMAND_INT_MAX_OUTPUT_SIZE 1

#endif /* FREERTOS_CONFIG_H_ */
