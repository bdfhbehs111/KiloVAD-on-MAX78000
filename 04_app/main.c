/* main.c */
#include <stdio.h>
#include <string.h>

#include "FreeRTOS.h"       /* 必须最先 */
#include "task.h"
#include "queue.h"          /* 不用队列就删 */
#include "semphr.h"         /* 不用信号量就删 */
#include "tasks_manage.h"
#include "mxc.h"            /* board.h / led.h / i2s.h / gpio.h / SEC / MSEC 全在里面 */

int main(void)
{
    /* 硬件必需的开机基线（不是"你的设计"，是前提） */
    Board_Init();
    MXC_ICC_Enable(MXC_ICC0);
    MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO);   /* 上电默认 60 MHz */
    SystemCoreClockUpdate();
    
    printf("\n*** BOOT OK ***\n");

    rtos_management();
    vTaskStartScheduler();

    for (;;) { }
}