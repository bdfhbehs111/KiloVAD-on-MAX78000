/******************************************************************************
 *
 * Copyright (C) 2022-2023 Maxim Integrated Products, Inc. (now owned by 
 * Analog Devices, Inc.),
 * Copyright (C) 2023-2024 Analog Devices, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 ******************************************************************************/

#ifndef APP_FREERTOSCONFIG_H_
#define APP_FREERTOSCONFIG_H_

/* ══════════════════════════════════════════════════════════════════════════
 *  来源：MSDK 原厂 Examples/MAX78000/FreeRTOSDemo/FreeRTOSConfig.h 的副本
 *        + 下面【两处】改动。其余数值与原厂逐字相同。
 *
 *  ── 改动 1：把「运行时间统计」从 DEBUG 开关里摘出来，默认关闭 ───────────
 *   原厂 `#if defined(DEBUG) && DEBUG == 1` 会打开
 *   configGENERATE_RUN_TIME_STATS，而它要求实现
 *   ConfigTimerForStats() / GetTimerForStats() —— 那是应用代码。
 *   而 MSDK 的 gcc.mk:443-444 在 DEBUG!=0 时会加 `-DDEBUG`，
 *   所以 DEBUG=1（本工程默认）会让原厂那份配置【直接链接失败】。
 *   → 要用就把下面的 USE_RUN_TIME_STATS 打开，并自己实现那两个函数。
 *
 *  ── 改动 2：configASSERT 无条件打开 ─────────────────────────────────────
 *   原厂把它放在 DEBUG==1 里，意味着 DEBUG=0 时 FreeRTOS 的所有内部检查
 *   （优先级合法性、栈、队列用法、FromISR 上下文…）全部消失。
 *   想关掉就注释掉下面那一段。
 *
 *  ── ⚠ 以下每一个数值都是【策略】，不是硬件限制。要改哪条直接改：
 *       configMAX_PRIORITIES     任务优先级档数
 *       configTOTAL_HEAP_SIZE    RTOS 堆大小（heap_4）
 *       INCLUDE_vTask*           各个 API 开不开
 *       configUSE_TRACE_FACILITY 任务状态查询
 *       configTICK_RATE_HZ       调度节拍
 * ══════════════════════════════════════════════════════════════════════════ */

#include <stdint.h>
#include "max78000.h"

/* ── 改动 1：运行时间统计（默认关；打开前你必须实现那两个函数）── */
/* #define USE_RUN_TIME_STATS 1 */
#if defined(USE_RUN_TIME_STATS)
extern void ConfigTimerForStats(void);
extern uint32_t GetTimerForStats(void);
#define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS() (ConfigTimerForStats())
#define portGET_RUN_TIME_COUNTER_VALUE() (GetTimerForStats())
#define configGENERATE_RUN_TIME_STATS 1
#endif

/* ── 改动 2：断言无条件打开 ── */
#define configASSERT(x)           \
    if ((x) == 0) {               \
        taskDISABLE_INTERRUPTS(); \
        for (;;) {}               \
    }
#define configENABLE_BACKWARD_COMPATIBILITY 1
#define configQUEUE_REGISTRY_SIZE 10
#define configRECORD_STACK_HIGH_ADDRESS 1

/*-----------------------------------------------------------
 * Application specific definitions.
 *
 * These definitions should be adjusted for your particular hardware and
 * application requirements.
 *
 * THESE PARAMETERS ARE DESCRIBED WITHIN THE 'CONFIGURATION' SECTION OF THE
 * FreeRTOS API DOCUMENTATION AVAILABLE ON THE FreeRTOS.org WEB SITE. 
 *
 * See http://www.freertos.org/a00110.html.
 *----------------------------------------------------------*/

/* CMSIS keeps a global updated with current system clock in Hz */
#define configCPU_CLOCK_HZ ((uint32_t)IPO_FREQ)

// #define configUSE_TICKLESS_IDLE     1

#define configTICK_RATE_HZ ((portTickType)1000)
#define configRTC_TICK_RATE_HZ (32768)

#define configTOTAL_HEAP_SIZE ((size_t)(26 * 1024))

#define configMINIMAL_STACK_SIZE ((uint16_t)128)

#define configMAX_PRIORITIES 5
#define configUSE_PREEMPTION 1
#define configUSE_IDLE_HOOK 0
#define configUSE_TICK_HOOK 0
#define configUSE_CO_ROUTINES 0
#define configUSE_16_BIT_TICKS 0
#define configUSE_MUTEXES 1

/* Run time and task stats gathering related definitions. */
#define configUSE_TRACE_FACILITY 1
#define configUSE_STATS_FORMATTING_FUNCTIONS 1

/* Set the following definitions to 1 to include the API function, or zero
to exclude the API function. */
#define INCLUDE_vTaskPrioritySet 0
#define INCLUDE_vTaskDelete 0
#define INCLUDE_vTaskSuspend 1
#define INCLUDE_vTaskDelayUntil 1
#define INCLUDE_uxTaskPriorityGet 0
#define INCLUDE_vTaskDelay 1

/* # of priority bits (configured in hardware) is provided by CMSIS */
#define configPRIO_BITS __NVIC_PRIO_BITS

/* Priority 7, or 255 as only the top three bits are implemented.  This is the lowest priority. */
#define configKERNEL_INTERRUPT_PRIORITY ((unsigned char)7 << (8 - configPRIO_BITS))

/* Priority 5, or 160 as only the top three bits are implemented. */
#define configMAX_SYSCALL_INTERRUPT_PRIORITY ((unsigned char)5 << (8 - configPRIO_BITS))

/* Alias the default handler names to match CMSIS weak symbols */
#define vPortSVCHandler SVC_Handler
#define xPortPendSVHandler PendSV_Handler
#define xPortSysTickHandler SysTick_Handler

#ifdef configUSE_TICKLESS_IDLE
/* Provide routines for tickless idle pre- and post- processing */
void vPreSleepProcessing(uint32_t *);
void vPostSleepProcessing(uint32_t);
#define configPRE_SLEEP_PROCESSING(idletime) vPreSleepProcessing(&idletime);
#define configPOST_SLEEP_PROCESSING(idletime) vPostSleepProcessing(idletime);
#endif

/* FreeRTOS+CLI requires this size to be defined, but we do not use it */
#define configCOMMAND_INT_MAX_OUTPUT_SIZE 1

#endif // APP_FREERTOSCONFIG_H_
