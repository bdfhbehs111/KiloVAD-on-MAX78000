#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把两个 ai8xize 生成的模型改名，使它们能在同一个工程里共存。

背景
----
哨兵和中文口令两个模型都由 ai8xize 生成，`cnn.c` / `cnn.h` 里的符号**完全同名**：

    cnn_enable / cnn_init / cnn_configure / cnn_load_weights / ... / cnn_time
    CNN_ISR / CNN_OK / CNN_FAIL / CNN_NUM_OUTPUTS(=1 与 =26，值还不一样！)
    memcpy32

直接放进一个工程必然重复定义 / 宏冲突。本脚本给每个模型的符号加前缀：

    哨兵      ->  sen_*      (sen_cnn_enable, SEN_CNN_ISR, ...)
    中文口令  ->  kws_*      (kws_cnn_enable, KWS_CNN_ISR, ...)

不改的东西
----------
- `CNN_INFERENCE_TIMER`：保持原名。它是编译期开关，两个模型共用一个宏定义即可
  同时打开推理计时（`cnn.c` 里 `#ifdef CNN_INFERENCE_TIMER` 用 `MXC_TMR_SW_*` 测周期数）。
- `weights.h`：里面只有 `KERNELS` / `BIAS_0..3` 这些**文件内宏**，每个 `*_cnn.c`
  各自 include 自己那份，不会跨编译单元冲突，故原样拷贝。
- `softmax.c`：两份**内容完全相同**（已核对哈希），只保留一份共用。

用法
----
    python namespace_models.py

输入： 01_models/sentinel_gate_bin2/max78000/sentinel/
      01_models/kws26_chinese/max78000/kws26/
输出： 04_app/models/sen/{sen_cnn.c, sen_cnn.h, weights.h}
      04_app/models/kws/{kws_cnn.c, kws_cnn.h, weights.h}
      04_app/models/softmax.c
"""

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # 04_app/tools
APP = HERE.parent                               # 04_app
ROOT = APP.parent                               # sys_agent_max78000

SOURCES = {
    "sen": ROOT / "01_models" / "sentinel_gate_bin2" / "max78000" / "sentinel",
    "kws": ROOT / "01_models" / "kws26_chinese" / "max78000" / "kws26",
}
OUT = APP / "models"

# 大写宏 / 明确定义的符号：整词替换
LITERAL = [
    ("__CNN_H__", "__{P}_CNN_H__"),
    ("CNN_NUM_OUTPUTS", "{P}_CNN_NUM_OUTPUTS"),
    ("CNN_FAIL", "{P}_CNN_FAIL"),
    ("CNN_OK", "{P}_CNN_OK"),
    ("CNN_START", "{P}_CNN_START"),
    ("CNN_COMPLETE", "{P}_CNN_COMPLETE"),
    ("CNN_ISR", "{P}_CNN_ISR"),
    ("SYS_START", "{P}_SYS_START"),
    ("SYS_COMPLETE", "{P}_SYS_COMPLETE"),
    ("memcpy32_const", "{p}_memcpy32_const"),
    ("memcpy32", "{p}_memcpy32"),
]
# 注意：CNN_INFERENCE_TIMER 故意不在此列 —— 保持原名，两个模型共用一个开关。

# 小写函数/变量前缀（覆盖 cnn_enable ... cnn_time 全部）
PREFIX = (r"\bcnn_", "{p}_cnn_")


def rename(text, p):
    P = p.upper()
    for lit, tpl in LITERAL:
        text = re.sub(r"\b" + re.escape(lit) + r"\b", tpl.format(p=p, P=P), text)
    text = re.sub(PREFIX[0], PREFIX[1].format(p=p, P=P), text)
    # 文件名也改了，对应的 #include 必须一起改，否则找不到头文件
    text = re.sub(r'#include\s+"weights\.h"', f'#include "{p}_weights.h"', text)
    text = re.sub(r'#include\s+"cnn\.h"', f'#include "{p}_cnn.h"', text)
    return text


def patch_header(text):
    """把 cnn.h 里"两模型完全相同"的部分抽到 model_common.h：

      - `typedef int32_t q31_t; typedef int16_t q15_t;`
        （原本在 cnn.h 里，共享的 softmax.c 就是靠它拿类型的）
      - `softmax_q17p14_q15` / `softmax_shift_q17p14_q15` 的原型

    抽走后，共享的 softmax.c 就不必依赖某一个具体模型的头文件，
    也不会出现两份重复 typedef。
    """
    text = re.sub(r"typedef\s+int32_t\s+q31_t\s*;\s*\n\s*typedef\s+int16_t\s+q15_t\s*;",
                  '#include "model_common.h"', text)
    text = re.sub(r"/\*[^*]*\*/\s*\n\s*void\s+softmax_q17p14_q15\([^;]*;\s*\n"
                  r"\s*/\*[^*]*\*/\s*\n\s*void\s+softmax_shift_q17p14_q15\([^;]*;",
                  "", text)
    text = re.sub(r"void\s+softmax_q17p14_q15\([^;]*;\s*\n", "", text)
    text = re.sub(r"void\s+softmax_shift_q17p14_q15\([^;]*;\s*\n", "", text)
    return text


MODEL_COMMON_H = """\
/**
 * @file    model_common.h
 * @brief   两个模型**完全相同**的部分：定点类型 + 共享 softmax。
 *
 * ⚠ 本文件由 04_app/tools/namespace_models.py 自动生成，请勿手改。
 *
 * 背景：ai8xize 会把 `q31_t` / `q15_t` 的 typedef 和 softmax 原型塞进
 * 每个模型的 cnn.h。两个模型各有一份 → 改名后若都 include 就会重复定义。
 * 这里抽成唯一来源，{sen,kws}_cnn.h 都 #include 它。
 */

#ifndef MODEL_COMMON_H_
#define MODEL_COMMON_H_

#include <stdint.h>

/* 定点类型（原本在 ai8xize 生成的 cnn.h 里） */
#ifndef MODEL_Q_TYPES_DEFINED
#define MODEL_Q_TYPES_DEFINED
typedef int32_t q31_t;
typedef int16_t q15_t;
#endif /* MODEL_Q_TYPES_DEFINED */

/* 定点 softmax（实现在 models/softmax.c，两个模型共用一份） */
void softmax_q17p14_q15(const q31_t *vec_in, const uint16_t dim_vec, q15_t *p_out);
void softmax_shift_q17p14_q15(q31_t *vec_in, const uint16_t dim_vec, uint8_t in_shift, q15_t *p_out);

#endif /* MODEL_COMMON_H_ */
"""


def main():
    for p, src in SOURCES.items():
        if not (src / "cnn.c").is_file():
            print(f"[ERR] 找不到源工程: {src}", file=sys.stderr)
            return 1

    OUT.mkdir(parents=True, exist_ok=True)
    report = []

    for p, src in SOURCES.items():
        d = OUT / p
        d.mkdir(parents=True, exist_ok=True)

        for old, new in (("cnn.c", f"{p}_cnn.c"), ("cnn.h", f"{p}_cnn.h")):
            txt = (src / old).read_text(encoding="utf-8", errors="replace")
            new_txt = rename(txt, p)
            if old == "cnn.h":
                new_txt = patch_header(new_txt)
            (d / new).write_text(new_txt, encoding="utf-8")
            report.append((f"models/{p}/{new}", len(txt), len(new_txt)))

        # weights.h 内的 KERNELS/BIAS_* 是文件局部宏，内容原样；仅改名避免重名歧义
        wh = (src / "weights.h").read_text(encoding="utf-8", errors="replace")
        (d / f"{p}_weights.h").write_text(wh, encoding="utf-8")
        report.append((f"models/{p}/{p}_weights.h", len(wh), "内容原样，仅改名"))

    # 共用一份 softmax.c（先核对两份一致）
    a = (SOURCES["sen"] / "softmax.c").read_bytes()
    b = (SOURCES["kws"] / "softmax.c").read_bytes()
    if a != b:
        print("[ERR] 两份 softmax.c 内容不同，不能共用！请人工确认。", file=sys.stderr)
        return 1
    # 原文件 include "cnn.h" 只是为了 q31_t/q15_t 和 softmax 原型，
    # 这两样都已抽到 model_common.h，改掉依赖。
    sm = a.decode("utf-8", errors="replace")
    sm = sm.replace('#include "cnn.h"', '#include "model_common.h"')
    (OUT / "softmax.c").write_text(sm, encoding="utf-8")
    report.append(("models/softmax.c", len(a), "两模型共用"))

    # 两模型完全相同的定点类型 + softmax 原型，抽成唯一来源
    (OUT / "model_common.h").write_text(MODEL_COMMON_H, encoding="utf-8")
    report.append(("models/model_common.h", len(MODEL_COMMON_H), "生成"))

    print("[OK] 模型改名完成")
    for name, old, new in report:
        print(f"     {name:<30} {old} -> {new}")

    # 自检：确认输出里不再有裸 cnn_ / CNN_ 符号。
    # 白名单 = CMSIS 设备头文件里定义的 `CNN_*`（如 CPU 级中断号 CNN_IRQn），
    # 那些是芯片定义、不是模型符号，必须保持原名。
    cmsis_dir = ROOT / "03_api" / "headers_cmsis"
    whitelist = set()
    for h in cmsis_dir.glob("*.h"):
        whitelist |= set(re.findall(r"\bCNN_\w+", h.read_text(encoding="utf-8", errors="replace")))
    # CNN_INFERENCE_TIMER 是编译期开关，故意保持原名
    whitelist.add("CNN_INFERENCE_TIMER")

    bad = []
    for f in sorted(OUT.rglob("*")):
        if f.suffix not in (".c", ".h") or f.name == "softmax.c":
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\b(?:cnn_\w+|CNN_\w*|memcpy32\w*|__CNN_H__)\b", txt):
            if m.group(0) in whitelist:
                continue
            bad.append(f"{f.relative_to(APP)}: {m.group(0)}")
    if bad:
        print("\n[WARN] 仍存在未加前缀的符号：")
        for x in sorted(set(bad))[:20]:
            print("   -", x)
        return 1
    print(f"     自检通过：无残留裸符号（已豁免 CMSIS 定义的 {len(whitelist)} 个 CNN_* 符号）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
