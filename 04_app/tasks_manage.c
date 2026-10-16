#include <stdio.h>
#include <string.h>

#include "mxc.h"
/* main.c */
#include <stdio.h>
#include <string.h>
#include "tasks_manage.h"
#include "FreeRTOS.h"       /* 必须最先 */
#include "task.h"
#include "queue.h"          /* 不用队列就删 */
#include "semphr.h"         /* 不用信号量就删 */
#include "mxc.h"            /* board.h / led.h / i2s.h / gpio.h / SEC / MSEC 全在里面 */
/* 两个改名后的模型（见 tools/namespace_models.py） */
#include "sen_cnn.h"
#include "kws_cnn.h"
static TaskHandle_t fifo_task_sentinel;
QueueHandle_t fifo_frame = NULL;
uint8_t a_pAI85Buffer[SAMPLE_SIZE];
uint8_t b_pAI85Buffer[SAMPLE_SIZE];
static int16_t x0, x1, Coeff;
static int32_t y0, y1;


/*==============================任务自用函数======================*/


static void HPF_init(void)
{
    Coeff = 32604; //0.995
    x0 = 0;
    y0 = 0;
    y1 = y0;
    x1 = x0;
}
static void i2s_isr(void)
{   
    BaseType_t higher_woken = pdFALSE;
    vTaskNotifyGiveFromISR(fifo_task_sentinel,&higher_woken);
    MXC_I2S_ClearFlags(MXC_F_I2S_INTFL_RX_THD_CH0);   
    portYIELD_FROM_ISR(higher_woken);  
}
static void HPF(int16_t input)
{
    int16_t Acc, output;
    int32_t tmp;

    /* a 1st order IIR high pass filter (100 Hz cutoff frequency)  */
    /* y(n)=x(n)-x(n-1)+A*y(n-1) and A =.995*2^15 */

    x0 = input;

    tmp = (Coeff * y1);
    Acc = (int16_t)((tmp + (1 << 14)) >> 15);
    y0 = x0 - x1 + Acc;

    /* Clipping */
    if (y0 > 32767) {
        y0 = 32767;
    }

    if (y0 < -32768) {
        y0 = -32768;
    }

    /* Update filter state */
    y1 = y0;
    x1 = x0;

    output = (int16_t)y0;

    return (output);
}
static uint8_t AddTranspose(uint8_t *pIn, uint8_t *pOut, uint16_t inSize, uint16_t outSize, uint16_t width)
{
    /* Data order in Ai85 memory (transpose is included):
    input(series of 8 bit samples): (0,0) ...  (0,127)  (1,0) ... (1,127) ...... (127,0)...(127,127)    16384 samples
    output (32bit word): 16K samples in a buffer. Later, each 1K goes to a seperate CNN memory group
    0x0000:
        (0,3)(0,2)(0,1)(0,0)
        (0,67)(0,66)(0,65)(0,64)
        (1,3)(1,2)(1,1)(1,0)
        (1,67)(1,66)(1,65)(1,64)
        ....
        (127,67)(127,66)(127,65)(127,64)
    0x0400:
        (0,7)(0,6)(0,5)(0,4)
        (0,71)(0,70)(0,69)(0,68)
        ....
        (127,71)(127,70)(127,69)(127,68)
    ...
    0x3C00:
        (0,63)(0,62)(0,61)(0,60)
        (0,127)(0,126)(0,125)(0,124)
        ....
        (127,127)(127,126)(127,125)(127,124)
    */

    static uint16_t row = 0, col = 0, total = 0;
    uint16_t secondHalf = 0, wordRow = 0, byteInWord = 0, group = 0, index = 0;

    for (int i = 0; i < inSize; i++) {
        /* is it above 63? */
        if (col >= (width >> 1)) {
            secondHalf = 1; // odd word rows
        } else {
            secondHalf = 0; // even word rows
        }

        /* which group (0-15) it should be */
        group = (col % (width >> 1)) / 4;

        /* which word row (0-255) within the group */
        wordRow = secondHalf + (row << 1);

        /* which byte (0-3) in the word */
        byteInWord = col % 4;

        /* find output index */
        index = 1024 * group + 4 * wordRow + byteInWord;

        /* place sample in correct output location */
        pOut[index] = pIn[i];

        total++;

        /* increment row and col index */
        col++;

        if (col >= width) {
            col = 0;
            row++;
        }
    }

    if (total >= outSize) {
        /* sanity check */
        if (row != width) {
            printf("ERROR: Rearranging!\n");
        }

        total = 0;
        row = 0;
        col = 0;
        return 1;
    } else  {
        return 0;
    }
}


/*=========================任务管理和任务本体函数===================*/

int rtos_management(){
    BaseType_t rc;
    fifo_frame = xQueueCreate(Q_FRAME_LEN, sizeof(uint8_t*)); //i2s（裸fifo）与cnn加速器之间连接的队列

    rc = xTaskCreate(vTaskAudioCapture_process, "audio",APP_STACK_AUDIO, NULL, APP_PRIO_AUDIO, &fifo_task_sentinel);
    if (rc != pdPASS) return 1;
    rc = xTaskCreate(vTaskCNN,"cnn_run",APP_STACK_CNN,NULL,APP_PRIO_CNN,NULL);
    if (rc != pdPASS) return 2;


    return 0;
}




static void vTaskAudioCapture_process(void* pv)
{   
    (void)pv;
    uint8_t ret = 0;  //偏置函数的专属标志位
    static uint8_t frame_drop_count=0;  //丢帧数目统计
    static uint8_t *cur_pAI85Buffer = a_pAI85Buffer;
    uint8_t pChunkBuff[CHUNK]; //第一波缓冲区，每个chunk有128个采样点
    static uint16_t chunkCount = 0;
    static uint32_t index = 0;
    uint16_t *ring[4]; //哑缓冲，过校验用的不用管
    int32_t err;
    mxc_i2s_req_t req;  //修改i2s的配置用的
    int32_t sample = 0;
    int16_t temp = 0;

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
    req.clkdiv      = 5;
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
    MXC_I2S_SetRXThreshold(8);
    MXC_I2S_EnableInt(MXC_F_I2S_INTEN_RX_THD_CH0);  //之后切换为丢帧的触发源头
    MXC_I2S_RXEnable();
    HPF_init();

    while (1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);  //阻塞，等待数据
        uint32_t n = MXC_I2S->dmach0 >> MXC_F_I2S_DMACH0_RX_LVL_POS;
        while ((n--) && (chunkCount < CHUNK)) {
                /* Copy captured microphone sample into i2s_rx_buffer. The actual value is 18 MSB of 32-bit word */
            sample = (int32_t)MXC_I2S->fifoch0;
            temp = sample >> 14;
            sample = HPF((int16_t)temp); 
            if (index < 10000) {index++;continue;} //丢弃前10000个样本，保证hpf的滤波算法正确
            pChunkBuff[chunkCount] = (uint8_t)((sample)*SAMPLE_SCALE_FACTOR / 256);
            chunkCount++;    
        }
        if (chunkCount == CHUNK){
            chunkCount = 0;//攒够 128 个采样点变成一个chunk才转置 ，作为预处理的准入条件
            ret = AddTranspose(pChunkBuff, cur_pAI85Buffer, CHUNK, SAMPLE_SIZE, TRANSPOSE_WIDTH);
                if(ret){  
                    uint8_t *p_ready = cur_pAI85Buffer;  // 刚填完的那块
                    // 发指针到队列
                    if (xQueueSend(fifo_frame, &p_ready, 0) != pdPASS) {
                        frame_drop_count++;
                        continue;
                    }
                    cur_pAI85Buffer = (cur_pAI85Buffer == a_pAI85Buffer) ? b_pAI85Buffer : a_pAI85Buffer;
                    ret = 0;
                }//攒够128个chunk进行一次预处理
        } 

    }
}


static void vTaskCNN(void *pv) {
    uint8_t *p_infer;
    while (1) {
        // 阻塞等，队列里有指针才返回
        if (xQueueReceive(fifo_frame, &p_infer, portMAX_DELAY) == pdPASS) {
            // p_infer 指向 a_pAI85Buffer 或 b_pAI85Buffer，直接送 CNN
            
        }
    }
}








