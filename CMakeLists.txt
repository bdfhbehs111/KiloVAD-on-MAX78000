# ============================================================================
#  sys_agent_max78000 —— 全目录编译统筹
#
#  用法（在 <本目录> 下）：
#
#     cmake -S . -B build -G Ninja                 # 配置（默认 MAXIM_PATH=D:/MaximSDK）
#     cmake -S . -B build -G Ninja -DMAXIM_PATH=E:/MaximSDK
#
#     cmake --build build --target app             # 只编 RTOS 应用（主力工程）
#     cmake --build build --target sentinel        # 只编哨兵独立工程
#     cmake --build build --target firmware        # 串行编全部四个（见下方说明）
#     cmake --build build --target app-size        # 看 Flash/SRAM 占用
#     cmake --build build --target app-flash       # 烧录
#     cmake --build build --target clean-all       # 全部清理
#     cmake --build build --target list-targets    # 列出所有目标
#
#  ⚠ 关于并行
#  --------
#  MSDK 把外设驱动编成**全工程共享**的静态库，放在
#  Libraries/PeriphDrivers/bin/<芯片>/<变体>/*.a。
#  因此**同时**编译多个工程会在建这个库时互相踩（表现为随机的
#  "Error 1" 而看不到任何编译错误）。
#  所以 `firmware` / `clean-all` 内部是**串行**执行的，别改成并行。
#  单独编一个工程（--target app）不受影响，可以放心 -j。
# ============================================================================

cmake_minimum_required(VERSION 3.20)

# 本工程不自己编译 C/C++（编译交给 MSDK 的 Makefile），
# 所以 LANGUAGES NONE，避免 CMake 去找编译器。
project(sys_agent_max78000 LANGUAGES NONE)

# ---------------------------------------------------------------------------
# MAXIM_PATH：命令行 -D 优先，其次环境变量，最后默认值
# ---------------------------------------------------------------------------
if(NOT MAXIM_PATH)
    if(DEFINED ENV{MAXIM_PATH})
        set(MAXIM_PATH "$ENV{MAXIM_PATH}")
    else()
        set(MAXIM_PATH "D:/MaximSDK")
    endif()
endif()
string(REPLACE "\\" "/" MAXIM_PATH "${MAXIM_PATH}")
set(SYSAGENT_MAXIM_PATH "${MAXIM_PATH}" CACHE PATH "MSDK 根目录")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
include(MsdkProject)

sysagent_discover_toolchain()

# ---------------------------------------------------------------------------
# 注册四个固件工程
# ---------------------------------------------------------------------------
# 主力工程：FreeRTOS 多任务应用（两个模型已合并改名）
sysagent_add_firmware(app 04_app BOARD FTHR_RevA)

# 两个模型的**独立**验证工程（各自带已知答案测试，单独跑通用的）
sysagent_add_firmware(sentinel 01_models/sentinel_gate_bin2/max78000/sentinel BOARD EvKit_V1)
sysagent_add_firmware(kws26 01_models/kws26_chinese/max78000/kws26 BOARD EvKit_V1)

# 官方 FreeRTOS 范例（参考基线）
sysagent_add_firmware(rtosdemo 02_rtos/MAX78000_FreeRTOSDemo BOARD EvKit_V1)

set(_all_fw app sentinel kws26 rtosdemo)

# ---------------------------------------------------------------------------
# 汇总目标：firmware（串行编全部）
# ---------------------------------------------------------------------------
set(_seq "${CMAKE_BINARY_DIR}/all_sequential.bat")
set(_seq_txt "@echo off\n")
string(APPEND _seq_txt "REM 由 CMake 生成：串行执行，避免共享 PeriphDrivers 库竞争\n")
foreach(_n IN LISTS _all_fw)
    string(APPEND _seq_txt "echo ==============================================\n")
    string(APPEND _seq_txt "echo   [${_n}]\n")
    string(APPEND _seq_txt "echo ==============================================\n")
    string(APPEND _seq_txt "call \"${CMAKE_BINARY_DIR}/fw_${_n}.bat\"\n")
    string(APPEND _seq_txt "if errorlevel 1 (echo [FAIL] ${_n} ^& exit /b 1)\n")
endforeach()
string(APPEND _seq_txt "echo.\necho [OK] 全部四个工程编译通过\n")
file(WRITE "${_seq}" "${_seq_txt}")

add_custom_target(firmware
    COMMAND cmd /c "${_seq}"
    COMMENT "Build ALL firmware sequentially"
    USES_TERMINAL VERBATIM)

# ---------------------------------------------------------------------------
# 汇总目标：clean-all（串行清理）
# ---------------------------------------------------------------------------
set(_cl "${CMAKE_BINARY_DIR}/all_clean.bat")
set(_cl_txt "@echo off\n")
foreach(_n IN LISTS _all_fw)
    string(APPEND _cl_txt "echo [clean] ${_n}\n")
    string(APPEND _cl_txt "call \"${CMAKE_BINARY_DIR}/fw_${_n}.bat\" clean\n")
endforeach()
file(WRITE "${_cl}" "${_cl_txt}")

add_custom_target(clean-all
    COMMAND cmd /c "${_cl}"
    COMMENT "Clean ALL firmware sequentially"
    USES_TERMINAL VERBATIM)

# clean 是 CMake 内置目标名，这里额外提供 clean-firmware 以免歧义
add_custom_target(clean-firmware
    COMMAND cmd /c "${_cl}"
    COMMENT "Clean ALL firmware sequentially"
    USES_TERMINAL VERBATIM)

# ---------------------------------------------------------------------------
# 帮助目标：列出所有可用目标
# ---------------------------------------------------------------------------
set(_help_txt "可用的 CMake 目标：\n\n")

# 把「完整标签」填充到固定宽度再跟说明，避免长短不一导致换行错乱
macro(_helpline label desc)
    string(LENGTH "${label}" _len)
    math(EXPR _pad "22 - ${_len}")
    if(_pad LESS 1)
        set(_pad 1)
    endif()
    string(REPEAT " " ${_pad} _sp)
    string(APPEND _help_txt "  ${label}${_sp}${desc}\n")
endmacro()

foreach(_n IN LISTS _all_fw)
    _helpline("${_n}" "build")
    _helpline("${_n}-clean" "clean")
    _helpline("${_n}-rebuild" "clean then build")
    _helpline("${_n}-size" "Flash / SRAM report")
    if(SYSAGENT_OPENOCD)
        _helpline("${_n}-flash" "flash to board")
        _helpline("${_n}-erase" "mass erase (careful)")
    endif()
    string(APPEND _help_txt "\n")
endforeach()
_helpline("firmware" "build ALL four sequentially")
_helpline("clean-all" "clean ALL sequentially")
_helpline("list-targets" "show this list")
file(WRITE "${CMAKE_BINARY_DIR}/targets.txt" "${_help_txt}")

add_custom_target(list-targets
    COMMAND "${CMAKE_COMMAND}" -E cat "${CMAKE_BINARY_DIR}/targets.txt"
    COMMENT "List available targets"
    VERBATIM)

# ---------------------------------------------------------------------------
# 配置期摘要
# ---------------------------------------------------------------------------
message(STATUS "")
message(STATUS "已注册固件工程：")
foreach(_n IN LISTS _all_fw)
    message(STATUS "  - ${_n}")
endforeach()
message(STATUS "")
message(STATUS "下一步：cmake --build build --target app")
message(STATUS "        cmake --build build --target list-targets   # 看全部目标")
message(STATUS "")
