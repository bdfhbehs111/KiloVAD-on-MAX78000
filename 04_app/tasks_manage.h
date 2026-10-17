#define APP_STACK_AUDIO  1024   
#define APP_PRIO_AUDIO   4
#define Q_FRAME_LEN    2 

#define APP_STACK_CNN 512
#define APP_PRIO_CNN 4


#define SAMPLE_SIZE 16384 // size of input vector for CNN, keep it multiple of 128
#define I2S_RX_BUFFER_SIZE 256
#define CHUNK 128 
// number of data points to read at a time and average for threshold, keep multiple of 128
#define TRANSPOSE_WIDTH 128
#define SAMPLE_SCALE_FACTOR 4 
// multiplies 16-bit samples by this scale factor before converting to 8-bit
typedef enum {
    STATE_SENTINEL = 0,      // 小模型常驻
    STATE_LOADING_HEAVY,     // 加载大模型
    STATE_HEAVY,             // 大模型推理中
    STATE_UNLOADING,         // 切回小模型
} model_state;
    /*设计四态状态机处理双模型协作：
    ┌──────────────────────────────────────────────────────┐
    │  STATE_SENTINEL（小模型常驻）                        │
    │  · CNN 加载小模型权重（1K参数）                      │
    │  · 每帧推理，检测异常                                │
    │  · 异常 → STATE_LOADING_HEAVY                        │
    ├──────────────────────────────────────────────────────┤
    │  STATE_LOADING_HEAVY（加载大模型到 CNN）              │
    │  · 暂停小模型推理                                    │
    │  · 权重从 Flash/ROM 搬到 weight SRAM                 │
    │  · 重配 CNN 寄存器（input dims, output classes...）  │
    │  · 加载完 → STATE_HEAVY                              │
    ├──────────────────────────────────────────────────────┤
    │  STATE_HEAVY（大模型推理）                            │
    │  · 处理当前帧 + 攒帧 buffer 里的历史帧               │
    │  · 推理完成 → 根据模式决定下一步                      │
    │  · 模式A（灵敏）→ 立刻回 STATE_SENTINEL              │
    │  · 模式B（省电）→ 继续 STATE_HEAVY 处理后续帧        │
    │  · 收到 Jetson "IDLE" → STATE_UNLOADING              │
    ├──────────────────────────────────────────────────────┤
    │  STATE_UNLOADING（切回小模型）                        │
    │  · 大模型权重从 weight SRAM 清掉                     │
    │  · 重新加载小模型权重                                │
    │  · 回到 STATE_SENTINEL                               │
    └──────────────────────────────────────────────────────┘\
    拥有双模式切换：模式一遇到异常立刻开kws推理
    模式二遇到异常攒起来，特定时间推理
    双模式通过agent或者人工配置
    */
int rtos_management(void);


static void vTaskCNN(void *pv);
static void vTaskAudioCapture_process(void* pv);
