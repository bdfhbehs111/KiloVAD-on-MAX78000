/******************************************************************************
 *
 * Copyright (C) 2022-2023 Maxim Integrated Products, Inc. (now owned by 
 * Analog Devices, Inc.),
 * Copyright (C) 2023-2026 Analog Devices, Inc.
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

/* ══════════════════════════════════════════════════════════════════════════
 *  max78000_app.ld —— 本工程的链接脚本
 *
 *  来源：MSDK 原厂 max78000.ld 的【逐字节副本】。
 *        本段注释以下的内容与原厂完全一致，未改一行结构。
 *
 *  ── 内存布局（"我们有多少内存"的唯一权威）────────────────────────────
 *  区域     起始          长度        大小        用途
 *  ──────── ──────────── ─────────── ─────────── ─────────────────────────
 *  ROM      0x00000000   0x00010000    64 KiB    片内 ROM（只读）
 *  FLASH    0x10000000   0x00080000   512 KiB    代码 + .rodata + .data 初值
 *  SRAM     0x20000000   0x0001FF80   130,944 B  .data/.bss/.heap/.stack 全在这
 *  SHARED   0x2001FF80   0x00000080       128 B  双核共享区
 *
 *  ⚠ 本工程是【单核 ARM】布局：M4F 独占 130,944 B SRAM。
 *    若改用双核（kws20_demo-riscv 那套），脚本会换成 max78000_arm.ld，
 *    它 include 的 common.ld 把 SRAM 劈成
 *      SRAM0 32K(.data/.bss) + SRAM1 32K(.heap/.stack) + SRAM2 48K(RV) + SRAM3 16K(RV)
 *    → M4F 可用量腰斩到 64 KiB。那是个大决定，别顺手做。
 *
 *  ── 有用的链接器符号（应用代码可 extern 引用）──────────────────────────
 *    _bss / _ebss          .bss 起止        → 开机清零范围 / 算实际占用
 *    _data / _edata        .data 起止
 *    __load_data           .data 的 Flash 源地址
 *    _shared / _eshared    SHARED 区起止
 *    __StackTop            栈顶（= SRAM 末尾，栈向下长）
 *    __HeapLimit           堆顶
 *
 *  ── 两条 ASSERT（编译期就报，不会到运行期才炸）────────────────────────
 *    "region RAM overflowed with stack"  → .data/.bss/.heap/.stack 超了 SRAM
 *    ".shared section overflow"          → SHARED 区超 128 B
 *
 *  ── 想预留固定区域（例如给某个缓冲池一个已知地址）─────────────────────
 *    SRAM 可用起点是 _ebss；栈从 __StackTop 往下；堆在 _ebss..__StackLimit。
 *    要抠一块出来，加一个 NOLOAD 段放在 .bss 之后：
 *
 *        .mypool (NOLOAD) :
 *        {
 *            . = ALIGN(32);
 *            _mypool = .;
 *            . += 0x8000;              // 32 KiB
 *            _emypool = .;
 *        } > SRAM
 *
 *    下面那条 ASSERT 会自动帮你检查放完之后还够不够栈。
 * ══════════════════════════════════════════════════════════════════════════ */

MEMORY {
    ROM        (rx) : ORIGIN = 0x00000000, LENGTH = 0x00010000 /* 64kB ROM */
    FLASH      (rx) : ORIGIN = 0x10000000, LENGTH = 0x00080000 /* 512KB Flash */
    SRAM      (rwx) : ORIGIN = 0x20000000, LENGTH = 0x0001FF80 /* ~128KB SRAM */
    SHARED     (rw) : ORIGIN = 0x2001FF80, LENGTH = 0x00000080 /* 128B Shared */
}

/* The address and length of the SHARED section defined above. */
__shared_origin = ORIGIN(SHARED);
__shared_length = LENGTH(SHARED);

SECTIONS {
    .rom :
    {
        KEEP(*(.rom_vector))
        *(.rom_handlers*)
    } > ROM

    .text :
    {
        _text = .;
        KEEP(*(.isr_vector))
        EXCLUDE_FILE (*riscv.o) *(.text*)    /* Program code (exclude RISCV code) */
        *(.rodata*)  /* read-only data: "const" */

        KEEP(*(.init))
        KEEP(*(.fini))

        /* .ctors */
        *crtbegin.o(.ctors)
        *crtbegin?.o(.ctors)
        *(EXCLUDE_FILE(*crtend?.o *crtend.o) .ctors)
        *(SORT(.ctors.*))
        *(.ctors)

        /* .dtors */
        *crtbegin.o(.dtors)
        *crtbegin?.o(.dtors)
        *(EXCLUDE_FILE(*crtend?.o *crtend.o) .dtors)
        *(SORT(.dtors.*))
        *(.dtors)

        /* C++ Exception handling */
        KEEP(*(.eh_frame*))
        _etext = .;
    } > FLASH

    .ARM.extab :
    {
        *(.ARM.extab* .gnu.linkonce.armextab.*)
    } > FLASH

    /* Binary import */
    .bin_storage :
    {
       FILL(0xFF)
      _bin_start_ = .;
      KEEP(*(.bin_storage_img))
      _bin_end_ = .;
      . = ALIGN(4);
    } > FLASH
    
    .rom_code :
    {
        . = ALIGN(16);
        _sran_code = .;
        *(.rom_code_section)
        _esran_code = .;
    } > ROM

    .flash_code :
    {
        . = ALIGN(16);
        _sran_code = .;
        *(.flash_code_section)
        _esran_code = .;
    } > FLASH

    .sram_code :
    {
        . = ALIGN(16);
        _sran_code = .;
        *(.sram_code_section)
        _esran_code = .;
    } > SRAM

    /* it's used for C++ exception handling      */
    /* we need to keep this to avoid overlapping */
    .ARM.exidx :
    {
        __exidx_start = .;
        *(.ARM.exidx* .gnu.linkonce.armexidx.*)
        __exidx_end = .;
    } > FLASH

    .data :
    {
        _data = ALIGN(., 4);
        *(vtable)
        *(.data*)           /*read-write initialized data: initialized global variable*/
        *(.flashprog*)      /* Flash program */

        /* These array sections are used by __libc_init_array to call static C++ constructors */
        . = ALIGN(4);
        /* preinit data */
        PROVIDE_HIDDEN (__preinit_array_start = .);
        KEEP(*(.preinit_array))
        PROVIDE_HIDDEN (__preinit_array_end = .);

        . = ALIGN(4);
        /* init data */
        PROVIDE_HIDDEN (__init_array_start = .);
        KEEP(*(SORT(.init_array.*)))
        KEEP(*(.init_array))
        PROVIDE_HIDDEN (__init_array_end = .);

        . = ALIGN(4);
        /* finit data */
        PROVIDE_HIDDEN (__fini_array_start = .);
        KEEP(*(SORT(.fini_array.*)))
        KEEP(*(.fini_array))
        PROVIDE_HIDDEN (__fini_array_end = .);

        _edata = ALIGN(., 4);
    } > SRAM AT>FLASH
    __load_data = LOADADDR(.data);

    .bss :
    {
        . = ALIGN(4);
        _bss = .;
        *(.bss*)     /*read-write zero initialized data: uninitialzed global variable*/
        *(COMMON)
        _ebss = ALIGN(., 4);
    } > SRAM

    /* We map the .shared section to a symbol rather than >SHARED to allow for backwards compatibility in CFS
     * with older projects that did not provide SHARED (note that CFS replaces the MEMORY command at the top of
     * this file). In that case, we just map to the end of memory.
     * We add an assert to ensure that the section fits in the available space.
     */
    PROVIDE(__shared_origin = 0x2001FFF8);
    PROVIDE(__shared_length = 8);

    .shared __shared_origin (NOLOAD) :
    {
        . = ALIGN(4);
        _shared = .;
        *(.mailbox*)
        . = ALIGN(4);
        *(.shared*)     /*read-write zero initialized data: uninitialzed global variable*/
        _eshared = ALIGN(., 4);
    }
    __shared_data = LOADADDR(.shared);

    ASSERT(SIZEOF(.shared) <= __shared_length, ".shared section overflow: exceeds inter-core shared memory region")

    /* Set stack top to end of RAM, and stack limit move down by
     * size of stack_dummy section */
    __StackTop = ORIGIN(SRAM) + LENGTH(SRAM);
    __StackLimit = __StackTop - SIZEOF(.stack_dummy);

    /* .stack_dummy section doesn't contains any symbols. It is only
     * used for linker to calculate size of stack sections, and assign
     * values to stack symbols later */
    .stack_dummy (COPY):
    {
        *(.stack*)
    } > SRAM

    .heap (COPY):
    {
        . = ALIGN(4);
        *(.heap*)
        __HeapLimit = ABSOLUTE(__StackLimit);
    } > SRAM

    PROVIDE(__stack = __StackTop);

    /* Check if data + heap + stack exceeds RAM limit */
    ASSERT(__StackLimit >= _ebss, "region RAM overflowed with stack")

    /* Section used by RISCV loader projects.  See RISCV_LOAD documentation in the build system. */
    .riscv_flash :
    {
        /* Align address to mod 256 with a small offset. This is required to match the flash page size.*/
        . = ALIGN(256); /* ALIGN operatator is used here.  Note that (. & 0x1FFFFF00) was used in the past, but a strange bug was seen on Windows where the & did not behave as expected.*/
        . += 0x100;
        _riscv_boot = .;
        KEEP(*riscv.o (.text*))
    } > FLASH
}
