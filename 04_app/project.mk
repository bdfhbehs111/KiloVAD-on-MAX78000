##############################################################################
# sys_agent MAX78000 应用 —— 工程配置
#
# 详细的 MSDK 构建系统说明：
#   https://analogdevicesinc.github.io/msdk/USERGUIDE/#build-system
#
# 本工程**不单独**手写 Makefile 规则；核心 Makefile（同目录的 Makefile）
# 会自动 glob 下面 VPATH 里的所有 *.c。
##############################################################################

# ── 目标板 ──────────────────────────────────────────────────────────────────
# FTHR_RevA : MAX78000FTHR，板载麦克风（本项目默认，I2S 采集要用）
# EvKit_V1  : MAX78000EVKIT，无板载麦克风，只能跑非音频部分
BOARD ?= FTHR_RevA

# ── FreeRTOS ───────────────────────────────────────────────────────────────
# 打开后 MSDK 会把 Libraries/FreeRTOS 编成 librtos.a 并链接进来。
LIB_FREERTOS = 1

# 堆分配方案：默认 4（heap_4，抗碎片，推荐）。
# 其余可选 1..5，对应 FreeRTOS/Source/portable/MemMang/heap_N.c
FREERTOS_HEAP_TYPE := 4
export FREERTOS_HEAP_TYPE

# FreeRTOS 需要的头文件路径（本目录下的 FreeRTOSConfig.h）
RTOS_CONFIG_DIR := .
export RTOS_CONFIG_DIR

# ── 源文件搜索路径 ─────────────────────────────────────────────────────────
# ⚠ VPATH 只管 .c 源文件；头文件必须用 IPATH，两者互不相通。
# 核心 Makefile 会执行：
#   SRCS += $(wildcard $(addsuffix /*.c, $(VPATH)))
# 所以把放 .c 的目录挂进来即可，不用手工维护文件清单。
VPATH += .
VPATH += models          # 两模型共用的 softmax.c
VPATH += models/sen      # 哨兵        sen_cnn.c
VPATH += models/kws      # 中文口令    kws_cnn.c

# 头文件搜索路径：main.c / app_tasks.c 要 include "sen_cnn.h" / "kws_cnn.h"
IPATH += models
IPATH += models/sen
IPATH += models/kws

# ── 调试 ───────────────────────────────────────────────────────────────────
# DEBUG=1 会打开 MSDK 的调试辅助（RTOS 运行统计定时器、可读的 HardFault 现场）
DEBUG = 1

# 优化级别：-Og 便于单步调试；出性能数时换成 -O2
# MXC_OPTIMIZE_CFLAGS = -Og

# ── 板子限制 ───────────────────────────────────────────────────────────────
ifeq ($(BOARD),Aud01_RevA)
$(error ERR_NOTSUPPORTED: 本工程不支持 Audio 板（沿用官方 FreeRTOSDemo 的限制）)
endif
