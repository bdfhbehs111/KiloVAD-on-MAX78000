# E7 功耗实测数据（MAX78000FTHR）

> 本目录存放 **实测功耗数据**。所有 CSV 由 `e7_power\tool\ut70cap.exe` 直接从上位机 DLL 采集，非手工抄录。

---

## 1. 测量链路

```
PC(USB-A) ──► UT70 A-IN
UT70 A-OUT ──A转micro-B──► MAX78000FTHR
UT70 Micro-USB HID ──► PC（上位机/DLL 通信）
```

**已验证**：UT70 的 D+/D- 直通成立 —— FTHR 的 DAPLink 完整枚举出 4 个接口
（大容量存储 MI_00、串口 COM3 MI_01、输入设备 MI_03、WebUSB CMSIS-DAP MI_04），
所以**功耗测量与串口日志可以同时进行**。

| 项 | 值 |
|---|---|
| UT70 HID | `USB\VID_19F5&PID_6666\ATKUT70`，序列号 `53B36640`，硬件版本 27 |
| 被测口 | `COM3` @ 115200（DAPLink 虚拟串口） |
| 测点 | VBUS（含 MAX78000 + 音频前端 + DAPLink + PMIC） |

---

## 2. 采集工具

`..\max78000\e7_power\tool\ut70cap.exe <秒数> <输出csv> [采样率]`

- 采样率可选 `4 / 10 / 50 / 200 / 500 / 1000`（SPS，默认 1000）
- 直接调用官方 `ATK_UT70DLL.dll` 的 `ReceCVDataEvent` 数据流，不经过 GUI
- 每秒 flush，可随时中断，已采到的数据不丢
- 结束打印 `mean_V / mean_I / mean_P / min_I / max_I / energy_Wh / energy_J`

CSV 列：`t_ms, V, I, P, Dp, Dm, R, Wh, AH`
（`t_ms` 是本机采集时刻，`Wh/AH` 是表内部计数值）

---

## 3. 文件命名

`<轮次>_<固件>_<时长>.csv`

| 固件代号 | 含义 |
|---|---|
| `vad` | 现役正式固件（vad_cnn，剪枝+蒸馏+QAT 后） |
| `sen1` | 旧基线固件（sen1_cnn，79,392 B 权重） |
| `idle` | 空转基线（无 CNN 推理） |

示例：`run02_vad_60min.csv`、`run03_idle_60min.csv`

---

## 4. 已测数据

### 4.1 `smoke_10s.csv` — 首次冒烟（2026-11-07，vad 固件，1000 SPS）

| 量 | 值 |
|---|---|
| 时长 | 10.12 s |
| 样本数 | 10,873（1074 /s） |
| 平均电压 | **5.24940 V** |
| 平均电流 | **13.18 mA** |
| 平均功率 | **69.17 mW** |
| 电流范围 | 11.97 ~ 14.16 mA |
| 表内能量计数 | 0.000195 Wh |
| 换算能量 | 0.703 J |

串口同时输出 `m=` 帧，实测帧周期 **1019 ms**（理论 1024 ms，偏差 0.5%）。

---

## 5. 已知限制（重要）

1. **1 Hz 的 CNN 推理突发看不出来**。1000 SPS 下电流只在 11.97~14.16 mA 之间平滑波动，
   没有可见的每秒尖峰 —— 原因是表内部对电流做了时间平均。
   → **单次推理能量不能用波形测，必须用「稳态差分 × t_inf」反推。**
2. **读数含 DAPLink**。表串在 VBUS 上，DAPLink(MAX32625) 的耗电一起算进去了。
   → 用「正式固件 − 空转固件」的差分消除。
3. **读数含表自身耗电**。UT70 从 A-IN 取电，其自身电流也流过采样电阻。
   → 同样靠差分消除；一切对比必须在同一链路下做。

---

## 6. 进展

- [x] `run01_vad_60min.csv` — vad 正式固件 1 h，**67.55 mW / 68.04 mWh**
- [x] `run02_hello_10min.csv` — Hello_World 基线 10 min，**48.33 mW**
- [x] `serial_1h.log` — 3,415 帧 margin，VOICE 16 帧（0.47 %）
  → **完整结论见 `E7_REPORT.md`**

### 待办（可选）

- [ ] `sen1` 固件 1 h（算剪枝在整板功耗上的收益）
- [ ] 电池供电（去掉 DAPLink）的真板级功耗
- [ ] 零偏标定（5 V + 100 Ω 1% 电阻 → 理论 50 mA）
- [ ] 「CNN 连跑」固件 → 差分实测 P_cnn

## 7. 参考文件

- `..\max78000\e7_power\_ref\` —— MAX20303 / FTHR / UT70 手册全文
- `..\max78000\e7_power\_lib\ATK_UT70DLL.dll` —— 官方上位机 DLL（x64）
- `..\max78000\e7_power\tool\ut70cap.cs` —— 采集工具源码
