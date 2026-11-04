#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 MAX78000 外设驱动头文件生成 API 速查表（markdown）。

输入:  03_api/headers/*.h           （MSDK 官方头文件原件，31 个）
输出:  03_api/periph/<name>.md      （按外设拆分的查表）
       03_api/_index.json          （机器可读索引: 函数名 -> 头文件/外设/章节）
       03_api/_global_functions.md （全局函数总表，按字母序）
       03_api/_periph_summary.md   （外设统计表）

用法（工作目录不限）:
    python gen_api_docs.py

解析要点（踩过的坑，勿轻易改动）:
 1. 花括号深度必须**跨 token 保持**。注释会出现在函数体内部，若按 token 独立
    切分语句，深度会错乱，`static inline` 定义会全部丢失。
 2. `__attribute__((deprecated("...")))` 要先用配平括号剥掉，否则会被当成函数名。
 3. 宏定义中"名字紧跟 `(`"才是函数式宏；`#define FOO (x)` 是对象式宏。
 4. 枚举成员可能跨行（`A = X |\n Y,`），须按"括号配平 + 行尾逗号"聚合。
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
API_DIR = HERE.parent
HDR_DIR = API_DIR / "headers"
OUT_DIR = API_DIR / "periph"
SRC_DIR = API_DIR / "source_ai85"

# 头文件名 -> 驱动源码子目录名（用于交叉引用；不一致处在此映射）
SRC_ALIAS = {
    "mxc.h": "SYS", "mxc_assert.h": "SYS", "mxc_delay.h": "SYS",
    "mxc_device.h": "SYS", "mxc_errors.h": "SYS", "mxc_lock.h": "SYS",
    "mxc_pins.h": "SYS", "mxc_sys.h": "SYS", "nvic_table.h": "SYS",
    "sema.h": "SEMA", "rtc.h": "RTC",
}

# 主标题用的中文名（未列出的用头文件 @brief 原文）
CN_NAME = {
    "adc": "ADC 逐次逼近模数转换器", "aes": "AES 硬件加解密引擎",
    "cameraif": "CameraIF 摄像头并行接口", "crc": "CRC 循环冗余校验",
    "dma": "DMA 直接存储器访问", "flc": "FLC 闪存控制器",
    "gpio": "GPIO 通用输入输出", "i2c": "I2C 总线", "i2s": "I2S 音频串行接口",
    "icc": "ICC 双核通信控制器", "lp": "LP 低功耗电源管理",
    "lpcmp": "LPCMP 低功耗比较器", "mxc": "MXC 总入口", "mxc_assert": "断言",
    "mxc_delay": "阻塞延时", "mxc_device": "器件宏", "mxc_errors": "错误码",
    "mxc_lock": "自旋锁", "mxc_pins": "引脚映射",
    "mxc_sys": "系统时钟/复位/外设使能", "nvic_table": "NVIC 中断向量表",
    "owm": "OWM 单总线(1-Wire)主机", "pt": "PT 脉冲序列发生器",
    "rtc": "RTC 实时时钟", "sema": "SEMA 硬件信号量", "spi": "SPI 总线",
    "tmr": "TMR 通用定时器", "trng": "TRNG 真随机数发生器", "uart": "UART 串口",
    "wdt": "WDT 看门狗", "wut": "WUT 唤醒定时器",
}

SEP_RE = re.compile(r"^/\*\s*[\*\-]{8,}\s*\*/\s*$")
ONE_LINE_COMMENT_RE = re.compile(r"^/\*\s*(.+?)\s*\*/\s*$")
# 单行横幅，如 `/***** Function Prototypes *****/`（至少 3 个 '*' 才认，避开 doxygen 的 /**）
SINGLE_BANNER_RE = re.compile(r"^/\*{3,}([^*].*?)\*+/\s*$")
IDENT_RE = re.compile(r"([A-Za-z_]\w*)\s*$")
CTRL_KEYWORDS = {
    "if", "else", "while", "for", "switch", "case", "do", "return",
    "sizeof", "defined", "static_assert", "_Static_assert", "assert",
}


# --------------------------------------------------------------------------
# 词法切分
# --------------------------------------------------------------------------
def tokenize(src, base_line=1):
    """切成 comment / code 两类 token，并记录起始行号。"""
    line_starts = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            line_starts.append(i + 1)

    def lineno(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return base_line + lo

    toks, i, n = [], 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            toks.append(("comment", src[i:j], lineno(i)))
            i = j
        elif src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j == -1 else j
            toks.append(("comment", src[i:j], lineno(i)))
            i = j
        else:
            j = i
            while j < n and not src.startswith("/*", j) and not src.startswith("//", j):
                j += 1
            if j > i:
                toks.append(("code", src[i:j], lineno(i)))
            i = j
    return toks


def clean_comment(text):
    """把 /* ... */ 或 // ... 变成纯文本，并剥掉 doxygen 标记 `///<` `/**<` `//!<`。"""
    if text.startswith("//"):
        return re.sub(r"^[/!]*<?[ \t]?", "", text[2:]).strip()
    body = text[2:-2] if text.endswith("*/") else text[2:]
    out = []
    for ln in body.splitlines():
        ln = re.sub(r"^\*+[ \t]?", "", ln.strip())
        ln = re.sub(r"^[/!]*<?[ \t]?", "", ln)
        out.append(ln)
    return "\n".join(out).strip()


def doxygen_field(block, field):
    m = re.search(r"@" + field + r"\s+(.*?)(?=\n\s*@|\Z)", block, re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip().rstrip("*").strip()


def is_doxygen(block):
    return block.lstrip().startswith("/**") or "@brief" in block


def strip_directives(code):
    """去掉预处理指令行（含 `\\` 续行的整条宏），避免污染语句切分。

    关键：`#define MXC_CRITICAL(code) {\\` 后面的续行体若被保留，
    里面的 `MXC_SYS_Crit_Enter();` 会被误判成一个函数声明。
    """
    out, cont = [], False
    for ln in code.splitlines():
        if cont:
            cont = ln.rstrip().endswith("\\")
            out.append("")
            continue
        if ln.lstrip().startswith("#"):
            cont = ln.rstrip().endswith("\\")
            out.append("")
            continue
        out.append(ln)
    return "\n".join(out)


def strip_attributes(s):
    """剥掉 __attribute__((...)) / __declspec(...)（配平括号扫描）。"""
    out, i = [], 0
    while i < len(s):
        m = re.compile(r"__(?:attribute__|attribute|declspec)").match(s, i)
        if m:
            k = m.end()
            while k < len(s) and s[k].isspace():
                k += 1
            if k < len(s) and s[k] == "(":
                depth, p = 0, k
                while p < len(s):
                    if s[p] == "(":
                        depth += 1
                    elif s[p] == ")":
                        depth -= 1
                        if depth == 0:
                            p += 1
                            break
                    p += 1
                i = p
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------
# 章节横幅：分割线 / 标题 / 分割线
# --------------------------------------------------------------------------
def banner_sections(lines):
    """收集章节横幅，支持两种官方写法：

        /* ***** */            三行式
        /* Title */
        /* ***** */

        /***** Title *****/    单行式
    """
    secs, i = [], 0
    while i < len(lines):
        if i + 2 < len(lines) and SEP_RE.match(lines[i]) and SEP_RE.match(lines[i + 2]):
            m = ONE_LINE_COMMENT_RE.match(lines[i + 1])
            if m and "@" not in m.group(1):
                secs.append((i + 3, m.group(1).strip()))
                i += 3
                continue
        m = SINGLE_BANNER_RE.match(lines[i])
        if m and re.search(r"[A-Za-z0-9\u4e00-\u9fff]", m.group(1)):
            secs.append((i + 1, m.group(1).strip()))
        i += 1
    return secs


def section_for(secs, lineno):
    cur = ""
    for at, title in secs:
        if at <= lineno:
            cur = title
        else:
            break
    return cur


# --------------------------------------------------------------------------
# 宏 / 枚举 / 结构体 / typedef / extern
# --------------------------------------------------------------------------
def parse_macros(code):
    """区分对象式/函数式宏：名字**紧跟** `(` 才是函数式宏。"""
    joined = re.sub(r"\\\r?\n", " ", code)
    out = []
    for line in joined.splitlines():
        m = re.match(r"[ \t]*#\s*define[ \t]+([A-Za-z_]\w*)", line)
        if not m:
            continue
        name, rest = m.group(1), line[m.end():]
        args = ""
        if rest.startswith("("):
            depth = 0
            for i, ch in enumerate(rest):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        args, rest = rest[: i + 1], rest[i + 1:]
                        break
            else:
                args, rest = rest, ""
        val = rest.strip()
        if not val and not args:
            continue
        doc = ""
        dm = re.search(r"/\*[*!<]*[ \t]*(.*?)[ \t]*\*/", val)
        if dm:
            doc, val = dm.group(1).strip(), val[: dm.start()].strip()
        val = re.sub(r"//.*$", "", val).strip()
        out.append((name + args, val, doc))
    return out


# 尾随式文档注释标记：`///<...`、`/**<...*/`、`//!<...`
TRAIL_MARK_RE = re.compile(r"^\s*(?:/\*[*!]*<|//[/!]*<)")


def _split_members(body):
    """把 enum/struct 体切成成员，并正确归属文档注释。

    两个关键点：
    1. `mxc_uart_regs_t *uart; ///<Point to UART registers` 里的注释在 `;`
       **之后**，属于**前一个**成员；若一律当"前导注释"，整篇文档会错位一行。
       多行 `///<` 续写要拼接。
    2. 必须按"顶层逗号/分号"逐字符切分，不能按行切——
       `MXC_LP_V0_9 = 0, MXC_LP_V1_0, MXC_LP_V1_1` 一行里有三个枚举成员。
    """
    members, cur, lead, depth, last_line = [], [], "", 0, -1
    for kind, text, tline in tokenize(body):
        if kind == "comment":
            d = re.sub(r"\s+", " ", clean_comment(text)).strip()
            d = re.sub(r"^@brief\s*", "", d).strip()
            if not d:
                continue
            # 两条判据任一成立即视为**尾随**注释（归属前一个成员）：
            #   a) 与前一个成员的结束符在同一行   —— wut.h 用 `///` 当尾随
            #   b) 带 `<` 标记（///< /**<）        —— uart.h 的多行续写独占一行
            if members and (tline == last_line or TRAIL_MARK_RE.match(text)):
                prev = members[-1]
                members[-1] = (prev[0], (prev[1] + " " + d).strip() if prev[1] else d)
            else:
                lead = d
            continue
        for off, ch in enumerate(text):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            if depth <= 0 and ch in ",;":
                txt = re.sub(r"\s+", " ", "".join(cur)).strip()
                cur = []
                if txt:
                    members.append((txt, lead))
                    lead = ""
                    last_line = tline + text.count("\n", 0, off)
                continue
            cur.append(ch)
    txt = re.sub(r"\s+", " ", "".join(cur)).strip()
    if txt:
        members.append((txt, lead))
    return members


def parse_enums(src):
    out = []
    for m in re.finditer(r"typedef\s+enum\s*\{(.*?)\}\s*([A-Za-z_]\w*)\s*;", src, re.S):
        members = _split_members(m.group(1))
        if members:
            out.append((m.group(2), members))
    return out


def parse_structs(src):
    """抽取结构体字段。头文件里结构体有三种写法，都要覆盖：

        1. typedef struct { ... } NAME;              （匿名）
        2. typedef struct TAG { ... } NAME;          （具名 + 别名）
        3. struct TAG { ... };                       （只有标签）
           typedef struct TAG NAME;                  （别名单独声明）

    用配平括号扫描取体，避免非贪婪 `.*?` 在嵌套结构体处提前截断。
    """
    alias = {t: n for t, n in re.findall(r"typedef\s+struct\s+(\w+)\s+(\w+)\s*;", src)}
    out, seen, consumed = [], set(), []

    for m in re.finditer(r"(?:typedef\s+)?struct\s*([A-Za-z_]\w*)?\s*\{", src):
        if any(a <= m.start() < b for a, b in consumed):
            continue
        start, depth, i = m.end(), 1, m.end()
        while i < len(src) and depth:
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
            i += 1
        if depth:
            continue
        body = src[start: i - 1]
        consumed.append((m.start(), i))

        tail = re.match(r"\s*([A-Za-z_]\w*)?\s*;", src[i:])
        tag = m.group(1)
        name = (tail.group(1) if tail else None) or alias.get(tag or "") or tag
        if not name or name in seen:
            continue
        fields = _split_members(body)
        if fields:
            seen.add(name)
            out.append((name, fields))
    return out


def parse_typedefs(src):
    out = []
    for m in re.finditer(r"typedef\s+([^;{}]*?\([\s\*]*\*?\s*([A-Za-z_]\w*)\s*\)\s*\([^)]*\))\s*;", src):
        out.append((m.group(2), re.sub(r"\s+", " ", m.group(1)).strip()))
    return out


def parse_externs(code):
    joined = re.sub(r"\\\r?\n", " ", strip_directives(code))
    out = []
    for m in re.finditer(r"\bextern\b([^;{}]*);", joined):
        decl = re.sub(r"\s+", " ", m.group(1)).strip()
        if "(" in decl:
            continue
        head = decl.rsplit("=", 1)[0].strip()
        nm = IDENT_RE.search(re.sub(r"\[[^\]]*\]\s*$", "", head).strip())
        if nm:
            out.append((nm.group(1), decl))
    return out


def parse_includes(src):
    return [m.group(1) for m in re.finditer(r'#\s*include\s+[<"]([^>"]+)[>"]', src)]


# --------------------------------------------------------------------------
# 函数抽取（单遍扫描，花括号深度跨 token 保持）
# --------------------------------------------------------------------------
def parse_header(path):
    src = path.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()
    secs = banner_sections(lines)

    m = re.search(r"@brief\s+(.*?)\n", src)
    file_brief = m.group(1).strip() if m else ""

    funcs, code_all = [], []
    pending = None
    depth = 0
    extern_c = 0          # `extern "C" {` 链接块计数（不能算进花括号深度）
    buf, buf_line, has_body = [], 1, False

    def flush():
        nonlocal buf, pending, has_body
        s = "".join(buf).strip()
        buf, has_body = [], False
        if "(" not in s:
            return
        dep = re.search(r'deprecated\s*\(\s*"([^"]*)"', s)
        clean = re.sub(r"\s+", " ", strip_attributes(s)).strip()
        if "(" not in clean or "typedef" in clean:
            pending = None
            return
        head = clean[: clean.index("(")].strip()
        if head.startswith("#") or "=" in head:
            pending = None
            return
        nm = IDENT_RE.search(head)
        if not nm or nm.group(1) in CTRL_KEYWORDS:
            pending = None
            return
        funcs.append({
            "name": nm.group(1),
            "proto": clean.rstrip(";").strip(),
            "brief": (pending or {}).get("brief", ""),
            "note": (pending or {}).get("note", ""),
            "deprecated": dep.group(1).strip() if dep else "",
            "section": section_for(secs, buf_line),
            "line": buf_line,
            "inline": "static inline" in clean,
        })
        pending = None

    for kind, text, line in toks_iter(src):
        if kind == "comment":
            if is_doxygen(text) and depth == 0:
                blk = clean_comment(text)
                b = doxygen_field(blk, "brief")
                if b:
                    pending = {"brief": b, "note": doxygen_field(blk, "note")}
            continue

        code_all.append(text)
        body = strip_directives(text)
        for off, ch in enumerate(body):
            if not buf and not ch.isspace():
                buf_line = line + body.count("\n", 0, off)

            if ch == "{":
                # `extern "C" {` 是链接声明块，不是函数体，不能进深度计数
                if depth == 0 and re.search(r'extern\s*"C"\s*$', "".join(buf).strip()):
                    extern_c += 1
                    buf = []
                    continue
                if depth == 0:
                    has_body = True
                depth += 1
                buf.append(ch)
                continue

            if ch == "}":
                if depth == 0 and extern_c > 0:
                    extern_c -= 1
                    buf = []
                    continue
                depth -= 1
                if depth <= 0:
                    depth = 0
                    if has_body:
                        flush()
                    # 收尾 '}' 必须丢弃：若留给下一个语句，buf 永远非空，
                    # buf_line 再也不会更新（行号全变成 1）
                    buf = []
                    continue
                buf.append(ch)
                continue

            buf.append(ch)
            if ch == ";" and depth == 0:
                flush()

    # 去重：同一函数常在 `#ifdef __riscv` / `#else` 两个分支各声明一次，
    # 保留说明更完整的那条，并记录变体数。
    merged, order = {}, []
    for f in funcs:
        k = f["name"]
        if k not in merged:
            merged[k] = f
            order.append(k)
            continue
        prev = merged[k]
        n = prev.get("variants", 1) + 1
        if (len(f["brief"]) + len(f["note"])) > (len(prev["brief"]) + len(prev["note"])):
            f["variants"] = n
            merged[k] = f
        else:
            prev["variants"] = n
    funcs = [merged[k] for k in order]

    code = "".join(code_all)
    return {
        "file": path.name, "stem": path.stem, "brief": file_brief,
        "funcs": funcs, "macros": parse_macros(code),
        "enums": parse_enums(src), "structs": parse_structs(src),
        "typedefs": parse_typedefs(src), "externs": parse_externs(code),
        "includes": parse_includes(src),
    }


def toks_iter(src):
    return tokenize(src)


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
def md_escape(s):
    return s.replace("|", "\\|")


def render(info):
    stem = info["stem"]
    cn = CN_NAME.get(stem, "")
    src_sub = SRC_ALIAS.get(info["file"], stem.upper())
    has_src = (SRC_DIR / src_sub).is_dir()

    L = [f"# `{info['file']}` — {cn}" if cn else f"# `{info['file']}`", ""]
    L.append(f"> **概要**：{info['brief'] or '（头文件无 @brief）'}")
    L.append(f"> **头文件**：`03_api/headers/{info['file']}`")
    L.append(f"> **驱动实现**：`03_api/source_ai85/{src_sub}/`" if has_src
             else "> **驱动实现**：（本芯片无独立源码，见通用实现）")
    L.append(f"> **函数** {len(info['funcs'])}　**宏** {len(info['macros'])}　"
             f"**枚举** {len(info['enums'])}　**结构体** {len(info['structs'])}　"
             f"**全局变量** {len(info['externs'])}")
    L += ["", "---", "", "## 目录", ""]
    for cond, label in [
        (info["structs"], "结构体"), (info["enums"], "枚举类型"),
        (info["typedefs"], "typedef"), (info["macros"], "宏定义"),
        (info["externs"], "预定义全局变量"),
    ]:
        if cond:
            L.append(f"- [{label}](#{label})")
    L += ["- [函数 API](#函数-api)"]
    if info["includes"]:
        L.append("- [依赖的其他头文件](#依赖的其他头文件)")
    L.append("")

    if info["structs"]:
        L += ["## 结构体", "", "> 调 API 前要先填这些结构体，字段名必须完全一致。", ""]
        for name, fields in info["structs"]:
            L += [f"### `{name}`", "", "| 字段 | 说明 |", "|---|---|"]
            for f, d in fields:
                L.append(f"| `{md_escape(f)}` | {md_escape(d)} |")
            L.append("")

    if info["enums"]:
        L += ["## 枚举类型", ""]
        for name, members in info["enums"]:
            L += [f"### `{name}`", "", "| 成员 | 说明 |", "|---|---|"]
            for mem, doc in members:
                L.append(f"| `{md_escape(mem)}` | {md_escape(doc)} |")
            L.append("")

    if info["typedefs"]:
        L += ["## typedef", "", "| 名称 | 原型 |", "|---|---|"]
        for n, p in info["typedefs"]:
            L.append(f"| `{n}` | `{md_escape(p)}` |")
        L.append("")

    if info["macros"]:
        L += ["## 宏定义", "", "| 宏 | 值 | 说明 |", "|---|---|---|"]
        for n, v, d in info["macros"]:
            v = v if len(v) <= 60 else v[:57] + "..."
            L.append(f"| `{md_escape(n)}` | `{md_escape(v)}` | {md_escape(d)} |")
        L.append("")

    if info["externs"]:
        L += ["## 预定义全局变量", "",
              "> SDK 已定义好的配置对象，直接取地址传给初始化函数即可，无需自己填。", "",
              "| 变量 | 声明 |", "|---|---|"]
        for n, d in info["externs"]:
            L.append(f"| `{n}` | `{md_escape(d)}` |")
        L.append("")

    L += ["## 函数 API", ""]
    if not info["funcs"]:
        L += ["_（本头文件无函数声明）_", ""]
    else:
        order, groups = [], {}
        for f in info["funcs"]:
            s = f["section"] or "（无章节标注）"
            if s not in groups:
                groups[s], _ = [], order.append(s)
            groups[s].append(f)
        for s in order:
            L += [f"### {s}", "", "| 函数原型 | 说明 |", "|---|---|"]
            for f in groups[s]:
                brief = md_escape(f["brief"])
                tags = []
                if f["inline"]:
                    tags.append("头文件内联实现")
                if f.get("variants", 1) > 1:
                    tags.append("多核分支重复声明，已合并")
                if f["deprecated"]:
                    tags.append(f"**已废弃**：{md_escape(f['deprecated'])}")
                if f["note"]:
                    tags.append(f"⚠ {md_escape(f['note'])}")
                if tags:
                    brief += "　" + "　".join(f"*{t}*" for t in tags)
                L.append(f"| `{md_escape(f['proto'])}` | {brief} |")
            L.append("")

    if info["includes"]:
        L += ["## 依赖的其他头文件", ""]
        L += [f"- `{inc}`" for inc in info["includes"]]
        L.append("")

    L += ["---", "",
          f"*本文件由 `03_api/tools/gen_api_docs.py` 从 `{info['file']}` 自动生成，"
          f"请勿手改；改脚本后重跑。*", ""]
    return "\n".join(L)


def main():
    if not HDR_DIR.is_dir():
        print(f"[ERR] 找不到头文件目录: {HDR_DIR}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    infos = sorted((parse_header(p) for p in sorted(HDR_DIR.glob("*.h"))),
                   key=lambda x: -len(x["funcs"]))

    index, rows, total = [], [], 0
    for info in infos:
        (OUT_DIR / (info["stem"] + ".md")).write_text(render(info), encoding="utf-8")
        total += len(info["funcs"])
        rows.append((info["stem"], info["file"], CN_NAME.get(info["stem"], ""),
                     len(info["funcs"]), len(info["macros"]),
                     len(info["enums"]), len(info["structs"])))
        for f in info["funcs"]:
            index.append({"name": f["name"], "proto": f["proto"], "brief": f["brief"],
                          "section": f["section"], "header": info["file"],
                          "periph": info["stem"], "deprecated": f["deprecated"],
                          "doc": f"03_api/periph/{info['stem']}.md"})

    (API_DIR / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    index.sort(key=lambda x: x["name"].lower())
    gl = ["# MAX78000 外设 API 全局函数总表", "",
          f"共 **{len(index)}** 个函数，按字母序排列。查表时 `Ctrl+F` 搜函数名。", "",
          "| 函数名 | 所属外设 | 头文件 | 查表 |", "|---|---|---|---|"]
    for it in index:
        gl.append(f"| `{it['name']}` | {it['periph']} | `{it['header']}` | "
                  f"[{it['periph']}.md](periph/{it['periph']}.md) |")
    gl.append("")
    (API_DIR / "_global_functions.md").write_text("\n".join(gl), encoding="utf-8")

    rows.sort(key=lambda x: -x[3])
    tl = ["# 外设 API 统计表", "",
          "| 外设 | 头文件 | 中文名 | 函数 | 宏 | 枚举 | 结构体 | 速查表 |",
          "|---|---|---|---:|---:|---:|---:|---|"]
    for stem, fn, cn, nf, nm, ne, ns in rows:
        tl.append(f"| `{stem}` | `{fn}` | {cn} | {nf} | {nm} | {ne} | {ns} | "
                  f"[{stem}.md](periph/{stem}.md) |")
    tl.append("")
    (API_DIR / "_periph_summary.md").write_text("\n".join(tl), encoding="utf-8")

    print(f"[OK] 头文件 {len(infos)} 个，函数 {total} 个")
    for f in ("periph\\*.md", "_index.json", "_global_functions.md", "_periph_summary.md"):
        print(f"     生成 {API_DIR}\\{f}")

    print("\n无函数声明的头文件:")
    for info in infos:
        if not info["funcs"]:
            print(f"  - {info['file']}")
    miss = [(i["file"], f["name"]) for i in infos for f in i["funcs"] if not f["brief"]]
    print(f"\n有函数但无 @brief 说明的 {len(miss)} 个:")
    for fn, nm in miss[:20]:
        print(f"  - {fn}: {nm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
