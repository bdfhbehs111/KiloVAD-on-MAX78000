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

void vTaskAudioCapture_process(void* pv);
