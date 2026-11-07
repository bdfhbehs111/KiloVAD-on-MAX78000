# -*- coding: utf-8 -*-
"""E7 energy analysis: UT70 CSV + firmware serial log -> summary report."""
import csv, os, re, sys, json, math
from collections import Counter

ROOT = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\energy_test"
CSV  = os.path.join(ROOT, "run01_vad_60min.csv")
SER  = os.path.join(ROOT, "serial_1h.log")
OUT  = os.path.join(ROOT, "analysis_run01.md")


def pct(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p / 100.0
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def analyze_power(path):
    t, V, I, P, Wh, AH = [], [], [], [], [], []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) < 9:
                continue
            try:
                t.append(float(row[0])); V.append(float(row[1])); I.append(float(row[2]))
                P.append(float(row[3])); Wh.append(float(row[7])); AH.append(float(row[8]))
            except ValueError:
                continue
    n = len(t)
    if n < 2:
        return {"error": "not enough samples", "n": n}

    # 时间轴（秒），去除重复/倒退
    t0 = t[0]
    ts = [(x - t0) / 1000.0 for x in t]
    dur = ts[-1]

    # 能量积分：梯形法 ∫V·I dt
    e_j = 0.0
    for k in range(1, n):
        dt = ts[k] - ts[k - 1]
        if dt <= 0 or dt > 5.0:      # 丢掉异常间隔
            continue
        e_j += 0.5 * (P[k] + P[k - 1]) * dt

    sI = sorted(I)
    sP = sorted(P)
    meanI = sum(I) / n
    meanP = sum(P) / n
    meanV = sum(V) / n
    varI = sum((x - meanI) ** 2 for x in I) / n

    # 漂移：前/后 5 分钟（时长不足 12 min 时无意义）
    w = 300.0
    if dur > 720:
        head = [I[k] for k in range(n) if ts[k] < w]
        tail = [I[k] for k in range(n) if ts[k] > dur - w]
        drift = (sum(tail) / len(tail) - sum(head) / len(head)) if head and tail else float("nan")
    else:
        drift = float("nan")

    # 1 Hz 周期性：10 ms 分箱 -> 去趋势(2 s 滑动平均) -> 自相关，只取前 120 s 控制耗时
    binms = 10.0
    nb = int(min(dur, 120.0) * 1000 / binms) + 1
    acc = [0.0] * nb; cnt = [0] * nb
    for k in range(n):
        b = int(ts[k] * 1000 / binms)
        if 0 <= b < nb:
            acc[b] += I[k]; cnt[b] += 1
    raw = [acc[b] / cnt[b] for b in range(nb) if cnt[b] > 0]
    # 滑动平均去趋势
    W = 200  # 2 s
    ser = []
    for b in range(len(raw)):
        lo = max(0, b - W // 2); hi = min(len(raw), b + W // 2 + 1)
        ser.append(raw[b] - sum(raw[lo:hi]) / (hi - lo))
    m = sum(ser) / len(ser) if ser else 0.0
    sd = math.sqrt(sum((x - m) ** 2 for x in ser) / len(ser)) if ser else 0.0
    peaks = []
    if sd > 1e-12 and len(ser) > 60:
        for lag in range(40, min(260, len(ser) // 2)):
            num = 0.0; den = 0.0
            for i in range(len(ser) - lag):
                a = ser[i] - m; b2 = ser[i + lag] - m
                num += a * b2; den += a * a
            if den > 0:
                peaks.append((num / den, lag * binms / 1000.0))
        peaks.sort(key=lambda x: -x[0])
    best = peaks[0] if peaks else (0.0, 0.0)
    top3 = peaks[:3]
    ripple_rms = sd

    return {
        "n": n, "duration_s": dur, "rate": n / dur if dur else 0,
        "mean_V": meanV, "mean_I": meanI, "mean_P": meanP,
        "min_I": sI[0], "max_I": sI[-1], "sd_I": math.sqrt(varI),
        "p05_I": pct(sI, 5), "p50_I": pct(sI, 50), "p95_I": pct(sI, 95),
        "min_P": sP[0], "max_P": sP[-1],
        "energy_J": e_j, "energy_mWh": e_j / 3.6,
        "energy_Wh": e_j / 3600.0,
        "dev_Wh_delta": Wh[-1] - Wh[0],
        "dev_AH_delta": AH[-1] - AH[0],
        "drift_mA": drift * 1000.0,
        "autocorr_peak": best[0], "autocorr_lag_s": best[1],
        "autocorr_top3": top3,
        "ripple_rms_mA": ripple_rms * 1000.0,
        "power_1h_mW": meanP * 1000.0,
        "energy_1h_mWh": meanP * 1000.0 * 1.0,
    }


LINE = re.compile(r"m=(-?\d+)\s+(VOICE|non)\s+miss=(\d+)")


def analyze_serial(path):
    margins, voice, miss_max, stamps = [], 0, 0, []
    other = Counter()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = ln.split("\t", 1)
            body = parts[1] if len(parts) == 2 else ln
            ts = float(parts[0]) / 1000.0 if len(parts) == 2 and parts[0].isdigit() else None
            mm = LINE.search(body)
            if mm:
                margins.append(int(mm.group(1)))
                if mm.group(2) == "VOICE":
                    voice += 1
                miss_max = max(miss_max, int(mm.group(3)))
                if ts is not None:
                    stamps.append(ts)
            else:
                other[body[:40]] += 1
    n = len(margins)
    if n == 0:
        return {"frames": 0, "other": dict(other)}
    sm = sorted(margins)
    span = (stamps[-1] - stamps[0]) if len(stamps) > 1 else 0.0
    # 帧周期：对 (序号, 时间戳) 做最小二乘拟合，斜率即平均帧周期
    # （DAPLink 会缓冲、轮询又有 200 ms 量化，单看时间跨度不可靠，拟合才稳）
    period_s = 0.0
    if len(stamps) > 20:
        nn = len(stamps)
        sx = float(nn * (nn - 1)) / 2.0
        sxx = float(nn * (nn - 1) * (2 * nn - 1)) / 6.0
        sy = sum(stamps)
        sxy = sum(i * stamps[i] for i in range(nn))
        den = nn * sxx - sx * sx
        if abs(den) > 1e-9:
            period_s = (nn * sxy - sx * sy) / den
    return {
        "frames": n, "voice": voice, "voice_pct": 100.0 * voice / n,
        "miss_max": miss_max,
        "margin_mean": sum(margins) / n, "margin_median": pct(sm, 50),
        "margin_min": sm[0], "margin_max": sm[-1],
        "margin_p05": pct(sm, 5), "margin_p95": pct(sm, 95),
        "margin_neg": sum(1 for x in margins if x < 0),
        "margin_neg_pct": 100.0 * sum(1 for x in margins if x < 0) / n,
        "span_s": span,
        "frame_hz": (1.0 / period_s) if period_s > 0 else 0.0,
        "period_ms": period_s * 1000.0,
        "other": dict(other),
    }


def fmt(v, nd=4):
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def main():
    res = {}
    if os.path.exists(CSV):
        res["power"] = analyze_power(CSV)
    else:
        res["power"] = {"error": "csv missing"}
    if os.path.exists(SER):
        res["serial"] = analyze_serial(SER)
    else:
        res["serial"] = {"error": "serial log missing"}

    p, s = res["power"], res["serial"]
    L = []
    L.append("# E7 实测分析 —— run01 (vad 固件, 1 h)\n")
    L.append(f"数据源：`{os.path.basename(CSV)}` + `{os.path.basename(SER)}`\n")
    L.append("## 1. 功耗\n")
    if "error" in p:
        L.append(f"无法分析：{p['error']}\n")
    else:
        rows = [
            ("时长", fmt(p["duration_s"], 1), "s"),
            ("样本数", p["n"], ""),
            ("实际采样率", fmt(p["rate"], 1), "样本/s"),
            ("平均电压", fmt(p["mean_V"], 5), "V"),
            ("平均电流", fmt(p["mean_I"] * 1000, 3), "mA"),
            ("**平均功率**", fmt(p["mean_P"] * 1000, 3), "mW"),
            ("电流标准差", fmt(p["sd_I"] * 1000, 3), "mA"),
            ("电流 min / P5 / P50 / P95 / max", "%s / %s / %s / %s / %s" % (
                fmt(p["min_I"] * 1000, 3), fmt(p["p05_I"] * 1000, 3), fmt(p["p50_I"] * 1000, 3),
                fmt(p["p95_I"] * 1000, 3), fmt(p["max_I"] * 1000, 3)), "mA"),
            ("CSV 积分能量", fmt(p["energy_J"], 3), "J"),
            ("CSV 积分能量", fmt(p["energy_mWh"], 4), "mWh"),
            ("表内 Wh 计数差", fmt(p["dev_Wh_delta"], 6), "Wh"),
            ("表内 AH 计数差", fmt(p["dev_AH_delta"], 6), "Ah"),
            ("首尾 5 min 漂移", fmt(p["drift_mA"], 3), "mA"),
            ("电流纹波 RMS（去 2 s 趋势）", fmt(p["ripple_rms_mA"], 3), "mA"),
            ("**自相关主峰**", "%s @ %s s" % (fmt(p["autocorr_peak"], 3), fmt(p["autocorr_lag_s"], 3)), ""),
            ("自相关次峰", "; ".join("%s@%ss" % (fmt(c, 3), fmt(l, 3)) for c, l in p["autocorr_top3"][1:]), ""),
            ("**1 h 推算能量**", fmt(p["mean_P"] * 1000, 3), "mWh"),
        ]
        L.append("| 项 | 值 | 单位 |\n|---|---|---|")
        for a, b, c in rows:
            L.append(f"| {a} | {b} | {c} |")
        L.append("")
    L.append("## 2. 固件串口（margin 分布）\n")
    if "error" in s or s.get("frames", 0) == 0:
        L.append(f"无有效帧：{s}\n")
    else:
        rows = [
            ("总帧数", s["frames"], ""),
            ("实际帧率", fmt(s["frame_hz"], 5), "Hz"),
            ("帧周期（最小二乘拟合）", fmt(s["period_ms"], 1), "ms"),
            ("覆盖时长", fmt(s["span_s"], 1), "s"),
            ("判为 VOICE 的帧", s["voice"], f"({fmt(s['voice_pct'],2)}%)"),
            ("margin 均值 / 中位数", "%s / %s" % (fmt(s["margin_mean"], 2), fmt(s["margin_median"], 2)), ""),
            ("margin min / P5 / P95 / max", "%s / %s / %s / %s" % (
                s["margin_min"], fmt(s["margin_p05"], 1), fmt(s["margin_p95"], 1), s["margin_max"]), ""),
            ("margin<0 帧数", s["margin_neg"], f"({fmt(s['margin_neg_pct'],2)}%)"),
            ("miss 计数最大值", s["miss_max"], ""),
        ]
        L.append("| 项 | 值 | 备注 |\n|---|---|---|")
        for a, b, c in rows:
            L.append(f"| {a} | {b} | {c} |")
        L.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("\n".join(L))
    print("\n--- JSON ---")
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
