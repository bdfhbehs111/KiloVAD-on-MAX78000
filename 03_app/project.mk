##############################################################################
# sys_agent MAX78000 -- 04_app 工程配置【模板】
#
#   本文件只干三件事（"创建模板"的边界）：
#     1) 挂必要的库
#     2) 指定链接脚本（内存布局）
#     3) 工具 / 优化 / 搜索路径开关
#
#   本文件【不含】任何应用逻辑、任务数量、结构体、变量。
#
#   构建系统说明：
#     https://analogdevicesinc.github.io/msdk/USERGUIDE/#build-system
#   同目录的核心 Makefile 会自动 glob 下面 VPATH 里的所有 *.c：
#     SRCS += $(wildcard $(addsuffix /*.c, $(VPATH)))
##############################################################################

# -- 目标板 ------------------------------------------------------------------
# FTHR_RevA : MAX78000FTHR（板载数字 MEMS 麦克风，I2S 采集用这块）
# EvKit_V1  : MAX78000EVKIT（无板载麦克风，音频部分跑不起来）
#
# 注意：这里必须用 `=` 而不是 `?=`。
#   核心 Makefile 的顺序是 `BOARD ?= EvKit_V1`（第 62 行）-> 再 include 本文件（第 94 行）。
#   所以本文件用 `?=` 时 BOARD 已经被赋成 EvKit_V1，这行就是【空操作】，
#   直接 `make` 会静默编成 EvKit 版本、麦克风完全不工作。
#   命令行传的 BOARD=... 优先级高于这里的 `=`，所以 CMake 那条路不受影响。
BOARD = FTHR_RevA

# -- FreeRTOS ----------------------------------------------------------------
# 置 1 -> MSDK 把 Libraries/FreeRTOS 编成 librtos.a 链接进来
LIB_FREERTOS = 1

# 堆分配方案：4 = heap_4（抗碎片，推荐）
# 可选 1..5，对应 Libraries/FreeRTOS/Source/portable/MemMang/heap_N.c
FREERTOS_HEAP_TYPE := 4
export FREERTOS_HEAP_TYPE

# FreeRTOS 的配置头从哪找（指到本目录的 FreeRTOSConfig.h）
RTOS_CONFIG_DIR := .
export RTOS_CONFIG_DIR

# -- 链接脚本（内存布局）-----------------------------------------------------
# 本目录 max78000_app.ld = 原厂 max78000.ld 的逐字节副本 + 内存预算注释。
# 布局：FLASH 512 KiB @0x10000000 | SRAM 130,944 B @0x20000000 | SHARED 128 B
#
# 注意：gcc.mk:686 把 LINKERFILE【原样】传给 -T，没有搜索路径，
#   所以这里必须是相对文件名或绝对路径。
LINKERFILE = max78000_app.ld

# -- 源文件 / 头文件搜索路径 -------------------------------------------------
# 注意：VPATH 只管 .c，头文件必须写进 IPATH，两者不相通。
#   以后要把模型或子目录挂进来，在这里加行，不用维护文件清单：
#       VPATH += models/sen
#       IPATH += models/sen
VPATH += .
IPATH += .

# 三个模型 + 共享 softmax：四个子目录都要挂，缺一个就会「模型不参与编译」或「头文件找不到」。
#   models      -> softmax.c   + model_common.h
#   models/sen  -> sen1_cnn.c + sen1_cnn.h / sen1_cnn_weights.h
#   models/vad  -> vad_cnn.c  + vad_cnn.h / vad_cnn_weights.h   （剪枝+自蒸馏，10,784 B）
#   models/kws  -> kws_cnn.c   + kws_cnn.h / kws_weights.h
VPATH += models models/sen models/vad models/kws
IPATH += models models/sen models/vad models/kws

# -- 调试 / 优化 -------------------------------------------------------------
# DEBUG=1 -> gcc.mk:443-444 加 `-g3 -ggdb -DDEBUG`，且优化级别变 -Og
#            （-DDEBUG 会定义 DEBUG 宏，FreeRTOSConfig.h 里已处理这个副作用）
# DEBUG=0 -> 默认 -O2，且不定义 DEBUG
DEBUG = 1

# 出性能数时用它覆盖：
# MXC_OPTIMIZE_CFLAGS = -O2

# -- 烧录工具链（OpenOCD）----------------------------------------------------
# 实测通过（板子 DAPLink 枚举正常）：OpenOCD 能连上 Cortex-M4，
#   flash 正确识别为 base 0x10000000 / size 512 KB。
#
# 由两处来源拼起来：
#   ① 可执行文件：D:\MaximSDK 自带的 xPack 通用版 OpenOCD
#      （来自安装器缓存 Tools\_downloads\openocd.zip，即 xpack-openocd-0.12.0-7）
#   ② TCL 配置：本项目树里 ai8x-synthesis\openocd\ 自带整套 MAX78000 配置
#      （max78000.cfg / interface\cmsis-dap.cfg / target\max32xxx.cfg /
#        target\swj-dp.tcl / mem_helper.tcl）
#
#   重要事实：ADI 的 MSDK 安装器【不】提供 max78000.cfg ——
#   它下载的 xPack 包里只有 max32620~max32690。这份 cfg 只存在于
#   ai8x-synthesis 里（那是 MAX78000 模型合成工具链，自带 OpenOCD 支持）。
#
# 已把 ② 的 5 个文件按 flash.mk 期望的布局复制到下面这个目录：
#   D:\MaximSDK\Tools\OpenOCD\scripts\
#       mem_helper.tcl
#       interface\cmsis-dap.cfg
#       target\max78000.cfg
#       target\max32xxx.cfg
#       target\swj-dp.tcl
#
# flash.mk:94 实际执行的是：
#   openocd -s ${OPENOCD_SCRIPTS} -f interface/${OPENOCD_ADAPTER}
#           -f target/${TARGET_LC}.cfg -c "program <hex> verify reset exit"
# 所以 max78000.cfg 必须落在 scripts\target\ 下，布局不能错。
#
# 注意：gcc.mk / flash.mk 里的路径用正斜杠，且不能带引号。
OPENOCD_SCRIPTS = D:/MaximSDK/Tools/OpenOCD/scripts

# flash.mk:45 默认 OPENOCDEXE ?= openocd.exe（隐含要求它在 PATH 上）。
# 这里给绝对路径，免得依赖 PATH 配置。
OPENOCDEXE = D:/MaximSDK/Tools/OpenOCD/xpack-openocd-0.12.0-7/bin/openocd.exe

# 调试器适配器：FTHR 板载 DAPLink（= flash.mk:37 的默认值 cmsis-dap.cfg）
OPENOCD_ADAPTER = cmsis-dap.cfg

# -- 板子限制 ----------------------------------------------------------------
ifeq ($(BOARD),Aud01_RevA)
$(error ERR_NOTSUPPORTED: 本工程不支持 Audio 板（沿用官方 FreeRTOSDemo 的限制）)
endif