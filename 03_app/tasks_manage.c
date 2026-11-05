#include <stdio.h>
#include <string.h>
#include "max20303.h"
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
#include "vad_cnn.h"
#include "kws_cnn.h"
static TaskHandle_t fifo_task_sentinel;
TaskHandle_t cnn_isr;

QueueHandle_t fifo_frame = NULL;
uint8_t a_pAI85Buffer[SAMPLE_SIZE];
uint8_t b_pAI85Buffer[SAMPLE_SIZE];
static int16_t x0, x1, Coeff;
static int32_t y0, y1;

/* 归一化要用的两个 libm 函数。
   不能 #include <math.h>：它顺带声明了 Bessel 函数 y0()/y1()，和上面 HPF 的
   状态变量重名，会直接编译报错。libm 由 gcc.mk:517 的 STD_LIBS=-lc -lm 链进来。 */
extern float sqrtf(float x);
extern float roundf(float x);


/*==============================任务自用函数======================*/

static uint8_t cnn_load_data(uint8_t *pIn)
{
    uint32_t mem;
    uint16_t index = 0;

    /* data should already be formated correctly */
    /* pIn is 16KB, each 1KB belongs to a memory group */
    for (mem = 0x50400000; mem <= 0x50418000; mem += 0x8000) {
        memcpy((uint8_t *)mem, &pIn[index], 1024);
        //printf("%.10X \n",(uint8_t *)mem);
        index += 1024;
    }

    for (mem = 0x50800000; mem <= 0x50818000; mem += 0x8000) {
        memcpy((uint8_t *)mem, &pIn[index], 1024);
        index += 1024;
    }

    for (mem = 0x50C00000; mem <= 0x50C18000; mem += 0x8000) {
        memcpy((uint8_t *)mem, &pIn[index], 1024);
        index += 1024;
    }

    for (mem = 0x51000000; mem <= 0x51018000; mem += 0x8000) {
        memcpy((uint8_t *)mem, &pIn[index], 1024);
        index += 1024;
    }

    return 1;
}
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
static int16_t HPF(int16_t input)
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
static void vTaskAudioCapture_process(void* pv);
static void vTaskCNN(void *pv);
int rtos_management(){
    BaseType_t rc;
    fifo_frame = xQueueCreate(Q_FRAME_LEN, sizeof(uint8_t*)); //i2s（裸fifo）与cnn加速器之间连接的队列

    rc = xTaskCreate(vTaskAudioCapture_process, "audio",APP_STACK_AUDIO, NULL, APP_PRIO_AUDIO, &fifo_task_sentinel);
    if (rc != pdPASS) return 1;
    rc = xTaskCreate(vTaskCNN,"cnn_run",APP_STACK_CNN,NULL,APP_PRIO_CNN,&cnn_isr);
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
                    /* 逐带归一化：对每个 col(通道/块内位置) 沿 row(时间块) 归一化。
                    base 对应 col，row=0..127 的采样在 cur_pAI85Buffer[base + 8*r]。 */
                    for (int col = 0; col < 128; col++) {
                        int group      = (col % 64) / 4;
                        int secondHalf = (col >= 64) ? 1 : 0;
                        int byteInWord = col % 4;
                        int base       = 1024 * group + 4 * secondHalf + byteInWord;

                        int32_t sum = 0;
                        for (int r = 0; r < 128; r++) sum += (int8_t)cur_pAI85Buffer[base + 8 * r];
                        float mean = (float)sum / 128.0f;

                        float var = 0.0f;
                        for (int r = 0; r < 128; r++) {
                            float d = (float)(int8_t)cur_pAI85Buffer[base + 8 * r] - mean;
                            var += d * d;
                        }
                        float std = sqrtf(var / 128.0f);

                        for (int r = 0; r < 128; r++) {
                            float xn = ((float)(int8_t)cur_pAI85Buffer[base + 8 * r] - mean) / (std + 1e-5f);
                            int32_t q = (int32_t)roundf(xn * 16.0f);   /* ×16，实测标定拐点 */
                            if (q > 127)  q = 127;
                            if (q < -128) q = -128;
                            cur_pAI85Buffer[base + 8 * r] = (uint8_t)(int8_t)q;
                        }
                    }
                    uint8_t *p_ready = cur_pAI85Buffer;   /* 归一化后再入队 */  
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
    static model_type current_model = SEN;   /* 加速器里装的是谁 */
    model_state state = IDLE;                /* 我在干什么 */
    uint8_t *p_infer;
    uint32_t sen_out2;
    uint32_t kws_out26[26]; 
    uint16_t miss_frame=0;
    vad_cnn_enable(MXC_S_GCR_PCLKDIV_CNNCLKSEL_PCLK, MXC_S_GCR_PCLKDIV_CNNCLKDIV_DIV1);
    vad_cnn_boost_enable(MXC_GPIO2, MXC_GPIO_PIN_5);
    vad_cnn_init();
    vad_cnn_load_weights();
    vad_cnn_load_bias();
    vad_cnn_configure();
    while (1) {
        switch (state)
        {
        case IDLE:
        if (xQueueReceive(fifo_frame, &p_infer, portMAX_DELAY) == pdPASS) {
            if(current_model==SEN) state=STATE_SENTINEL;
            else {
                miss_frame++;
                /*此情况出现意味着设备在处理复杂数据kws的时候有当前音频数据溢出了/系统出现故障了，之后加个缓冲区专门处理或者上报错误日志，
                在state_sentinel里面将优先处理缓冲区的内容*/
            }
        }
        break;
        case STATE_SENTINEL:
        while (ulTaskNotifyTake(pdTRUE, 0) != 0) { }   /*等价于清空标志位，为了防止数据结果有误，i2s不使用因为意外唤醒有while的条件判断兜底，且前一万个样本作废*/
        cnn_load_data(p_infer);
        vad_cnn_start();
        if (ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(50)) == 0) {
            miss_frame++;                                   /* 超时，绝不死等 */
            state = IDLE;
            break;   //等待isr中断通知
        }
        vad_cnn_unload(&sen_out2);
        int8_t s0 = (int8_t)(sen_out2 & 0xff);
        int8_t s1 = (int8_t)((sen_out2 >> 16) & 0xff);

        int margin = (int)s0 - (int)s1;
        /* 类 0 = 非人声(s0)，类 1 = 人声(s1) → margin = s0 - s1 < 0 才是人声 */
        printf("m=%d %s miss=%u\n", margin, margin < 0 ? "VOICE" : "non", miss_frame);
        state = IDLE;
        break;
        case STATE_LOADING_HEAVY:
        
        
        state = IDLE;
        break;
        case STATE_HEAVY:


        state = IDLE;
        break;
        case STATE_UNLOADING:


        state = IDLE;
        break;

        }

            
            
        }
}









