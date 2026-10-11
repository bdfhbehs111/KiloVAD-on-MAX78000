# ============================================================================
#  MsdkProject.cmake —— 把 MSDK 的 Makefile 工程接进 CMake
#
#  设计取舍
#  --------
#  MSDK 官方构建系统是 **Makefile**（不是 CMake），并且深度依赖
#  `Libraries/*.mk`、`project.mk`、`MAXIM_PATH` 这一套。用 CMake 重写整个
#  BSP/外设驱动构建既庞大又极易和官方脱节。
#
#  所以这里采用「CMake 做编排，Make 做编译」：
#    - CMake 负责：定位工具链、统一环境、批量/增量的目标管理、尺寸报告
#    - Make 负责：真正的编译链接（沿用官方规则，不改一行）
#
#  每个工程会生成一个 `<build>/<name>.bat` 包装脚本，在里面设好
#  MAXIM_PATH 和 PATH 再调 make —— 这样彻底避开 CMake 传 PATH 时
#  分号被当列表分隔符的坑。
# ============================================================================

if(NOT WIN32)
    message(FATAL_ERROR "本套编排脚本只面向 Windows（MSDK 工具链是 Windows 版）")
endif()

# ---------------------------------------------------------------------------
# 一、工具链发现
# ---------------------------------------------------------------------------

# 在 <base>/<prefix>* 里挑版本号最大的那个目录（目录名按字典序排即版本序）
function(_sysagent_pick_dir out base prefix)
    file(GLOB _cands "${base}/${prefix}*")
    if(NOT _cands)
        set(${out} "" PARENT_SCOPE)
        return()
    endif()
    list(SORT _cands)
    list(REVERSE _cands)
    list(GET _cands 0 _best)
    set(${out} "${_best}" PARENT_SCOPE)
endfunction()

function(sysagent_discover_toolchain)
    if(NOT EXISTS "${SYSAGENT_MAXIM_PATH}")
        message(FATAL_ERROR
            "找不到 MAXIM_PATH = ${SYSAGENT_MAXIM_PATH}\n"
            "请用 -DMAXIM_PATH=<MSDK 根目录> 指定，例如 -DMAXIM_PATH=D:/MaximSDK")
    endif()

    # --- arm-none-eabi 工具链 ---
    _sysagent_pick_dir(_gcc_dir "${SYSAGENT_MAXIM_PATH}/Tools/GNUTools"
                       "xpack-arm-none-eabi-gcc-")
    if(_gcc_dir AND EXISTS "${_gcc_dir}/bin/arm-none-eabi-gcc.exe")
        set(_gcc_bin "${_gcc_dir}/bin")
    else()
        find_program(_gcc arm-none-eabi-gcc)
        if(_gcc)
            get_filename_component(_gcc_bin "${_gcc}" DIRECTORY)
        else()
            message(FATAL_ERROR
                "找不到 arm-none-eabi-gcc。\n"
                "  期望位置：${SYSAGENT_MAXIM_PATH}/Tools/GNUTools/xpack-arm-none-eabi-gcc-*/bin\n"
                "  或把它加进 PATH。")
        endif()
    endif()

    # --- make（MSDK 自带 MSYS2 的 make）---
    set(_make "${SYSAGENT_MAXIM_PATH}/Tools/MSYS2/msys64/usr/bin/make.exe")
    if(NOT EXISTS "${_make}")
        find_program(_make_alt make)
        if(_make_alt)
            set(_make "${_make_alt}")
        else()
            message(FATAL_ERROR
                "找不到 make。\n"
                "  期望位置：${SYSAGENT_MAXIM_PATH}/Tools/MSYS2/msys64/usr/bin/make.exe")
        endif()
    endif()
    get_filename_component(_make_bin "${_make}" DIRECTORY)

    # --- OpenOCD（烧录用；缺失只警告，不阻塞编译）---
    _sysagent_pick_dir(_ocd_dir "${SYSAGENT_MAXIM_PATH}/Tools/OpenOCD"
                       "xpack-openocd-")
    if(_ocd_dir AND EXISTS "${_ocd_dir}/bin/openocd.exe")
        set(_ocd "${_ocd_dir}/bin/openocd.exe")
        set(_ocd_bin "${_ocd_dir}/bin")
        # 官方 flash.mk 期望 ${MAXIM_PATH}/Tools/OpenOCD/scripts；
        # xpack 自带的是 <ver>/openocd/scripts，两者都试
        if(EXISTS "${SYSAGENT_MAXIM_PATH}/Tools/OpenOCD/scripts")
            set(_ocd_scripts "${SYSAGENT_MAXIM_PATH}/Tools/OpenOCD/scripts")
        else()
            set(_ocd_scripts "${_ocd_dir}/openocd/scripts")
        endif()
    else()
        set(_ocd "")
        set(_ocd_bin "")
        set(_ocd_scripts "")
    endif()

    # --- arm-none-eabi-size（尺寸报告）---
    if(EXISTS "${_gcc_bin}/arm-none-eabi-size.exe")
        set(_size "${_gcc_bin}/arm-none-eabi-size.exe")
    else()
        set(_size "")
    endif()

    # --- 导出到调用者（顶层目录）作用域 ---
    set(SYSAGENT_GCC_BIN "${_gcc_bin}" PARENT_SCOPE)
    set(SYSAGENT_MAKE "${_make}" PARENT_SCOPE)
    set(SYSAGENT_MAKE_BIN "${_make_bin}" PARENT_SCOPE)
    set(SYSAGENT_OPENOCD "${_ocd}" PARENT_SCOPE)
    set(SYSAGENT_OPENOCD_BIN "${_ocd_bin}" PARENT_SCOPE)
    set(SYSAGENT_OPENOCD_SCRIPTS "${_ocd_scripts}" PARENT_SCOPE)
    set(SYSAGENT_SIZE "${_size}" PARENT_SCOPE)

    message(STATUS "MAXIM_PATH   : ${SYSAGENT_MAXIM_PATH}")
    message(STATUS "arm-none-eabi: ${_gcc_bin}")
    message(STATUS "make         : ${_make}")
    message(STATUS "arm-size     : ${_size}")
    if(_ocd)
        message(STATUS "openocd      : ${_ocd}")
        message(STATUS "ocd scripts  : ${_ocd_scripts}")
    else()
        message(WARNING "找不到 OpenOCD，flash-* 目标将不可用")
    endif()
endfunction()

# ---------------------------------------------------------------------------
# 二、注册一个固件工程
#     sysagent_add_firmware(<name> <相对目录> [BOARD <板子>] [TARGET <芯片>])
#
#   生成目标：
#     <name>         编译
#     <name>-clean   清理
#     <name>-rebuild 清理后重编
#     <name>-size    打印 Flash/SRAM 占用
#     <name>-flash   烧录（需要 OpenOCD 支持该芯片）
#     <name>-erase   全片擦除
# ---------------------------------------------------------------------------
function(sysagent_add_firmware name dir)
    cmake_parse_arguments(ARG "" "BOARD;TARGET" "" ${ARGN})
    if(NOT ARG_BOARD)
        set(ARG_BOARD "EvKit_V1")
    endif()
    if(NOT ARG_TARGET)
        set(ARG_TARGET "MAX78000")
    endif()

    set(_proj "${CMAKE_SOURCE_DIR}/${dir}")
    if(NOT EXISTS "${_proj}/Makefile")
        message(FATAL_ERROR "${name}: ${_proj} 下没有 Makefile，不是 MSDK 工程")
    endif()

    # MSDK 需要正斜杠形式的 MAXIM_PATH
    string(REPLACE "\\" "/" _maxim_fwd "${SYSAGENT_MAXIM_PATH}")
    file(TO_NATIVE_PATH "${_proj}" _proj_native)

    # ---- 生成包装脚本：设好环境再调 make ----
    #
    # ⚠ 必须用 string(APPEND) 逐行拼**单个字符串**。
    #   若用 `set(_lines "a" "b" "c")` 再 join，PATH 里的 `;` 会被 CMake
    #   当成列表分隔符切开，生成出 4 行残缺的 set PATH=...（踩过）。
    set(_sh "${CMAKE_BINARY_DIR}/fw_${name}.bat")
    set(_jobs "$ENV{NUMBER_OF_PROCESSORS}")
    if(NOT _jobs)
        set(_jobs 4)
    endif()

    set(_script "@echo off\n")
    string(APPEND _script "REM 由 CMake 生成，勿手改。包装 MSDK 的 Makefile 构建。\n")
    string(APPEND _script "set \"MAXIM_PATH=${_maxim_fwd}\"\n")
    string(APPEND _script "set \"PATH=${SYSAGENT_GCC_BIN};${SYSAGENT_MAKE_BIN};${SYSAGENT_OPENOCD_BIN};%PATH%\"\n")
    string(APPEND _script "cd /d \"${_proj_native}\"\n")
    string(APPEND _script "\"${SYSAGENT_MAKE}\" -r -j ${_jobs} --output-sync=target --no-print-directory TARGET=${ARG_TARGET} BOARD=${ARG_BOARD} MAXIM_PATH=${_maxim_fwd} %*\n")
    string(APPEND _script "exit /b %ERRORLEVEL%\n")
    file(WRITE "${_sh}" "${_script}")

    # ---- 编译 ----
    add_custom_target(${name}
        COMMAND cmd /c "${_sh}"
        WORKING_DIRECTORY "${_proj}"
        COMMENT "Build ${name} (BOARD=${ARG_BOARD})"
        USES_TERMINAL VERBATIM)

    # ---- 清理 ----
    add_custom_target(${name}-clean
        COMMAND cmd /c "${_sh}" clean
        WORKING_DIRECTORY "${_proj}"
        COMMENT "Clean ${name}"
        USES_TERMINAL VERBATIM)

    # ---- 清理后重编 ----
    add_custom_target(${name}-rebuild
        COMMAND cmd /c "${_sh}" clean
        COMMAND cmd /c "${_sh}"
        WORKING_DIRECTORY "${_proj}"
        COMMENT "Rebuild ${name}"
        USES_TERMINAL VERBATIM)

    # ---- 尺寸报告 ----
    set(_elf "${_proj}/build/max78000.elf")
    if(SYSAGENT_SIZE)
        add_custom_target(${name}-size
            COMMAND "${SYSAGENT_SIZE}" --format=berkeley "${_elf}"
            COMMAND "${SYSAGENT_SIZE}" -A "${_elf}"
            COMMENT "Size report for ${name}"
            VERBATIM)
    endif()

    # ---- 烧录 ----
    if(SYSAGENT_OPENOCD)
        # 官方 flash.mk 的等价命令：program <hex> verify reset exit
        set(_hex "${_proj}/build/max78000.hex")
        add_custom_target(${name}-flash
            COMMAND "${CMAKE_COMMAND}" -E echo
                    "烧录 ${name}（需要 target/max78000.cfg，见根目录 README 的『烧录』一节）"
            COMMAND "${SYSAGENT_OPENOCD}"
                    -s "${SYSAGENT_OPENOCD_SCRIPTS}"
                    -f "interface/cmsis-dap.cfg"
                    -f "target/max78000.cfg"
                    -c "program ${_hex} verify reset exit"
            DEPENDS ${name}
            COMMENT "Flash ${name}"
            USES_TERMINAL VERBATIM)

        add_custom_target(${name}-erase
            COMMAND "${SYSAGENT_OPENOCD}"
                    -s "${SYSAGENT_OPENOCD_SCRIPTS}"
                    -f "interface/cmsis-dap.cfg"
                    -f "target/max78000.cfg"
                    -c "init; reset halt; max32xxx mass_erase 0;"
                    -c "exit"
            COMMENT "Mass erase ${name}"
            USES_TERMINAL VERBATIM)
    endif()

    set(SYSAGENT_FIRMWARE_TARGETS ${SYSAGENT_FIRMWARE_TARGETS} ${name}
        CACHE INTERNAL "已注册的固件工程")
endfunction()
