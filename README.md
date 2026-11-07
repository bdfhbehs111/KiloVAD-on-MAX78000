# 声学哨兵 · MAX78000 边缘 VAD 系统

> `project-egde_cnn_vad` —— 在 **MAX78000FTHR** 上跑一个 8-bit 定点语音活动检测（VAD）CNN，
> 从数据制备、模型训练、剪枝蒸馏、量化部署，一直到板上实测功耗的**完整闭环**。

| 项 | 值 |
|---|---|
| 目标硬件 | MAX78000FTHR（Cortex-M4F + CNN 加速器） |
| 任务 | 二分类：`nonvoice` / `voice` |
| 模型 | `KiloVAD_MAX`，7 层 1-D CNN，**10,784 B** int8 权重 |
| 精度（int8，与板上一致） | val AUC **0.99526**，test AUC **0.99542**，test FPR **1.18 %** |
| 硬件开销 | **814,512 ops**（800,928 macc），权重占 CNN 存储 **2.4 %** |
| 固件占用 | FLASH **67,876 B**，SRAM **63,464 B** |
| **整板 1 h 平均功耗** | **67.55 mW**（VBUS 输入，含板上调试器） |
| **单次推理能量** | **3.22 µJ**（官方 4.02 pJ/MAC × 800,928） |
| 推理占空比 | 0.075 %（0.76 ms / 1020 ms 帧周期） |

---

## 一、三大板块

| 板块 | 目录 | 一句话 |
|---|---|---|
| **软件框架** | `01_rtos` / `02_api` / `03_app` / `cmake` | FreeRTOS + MSDK 外设层 + 应用任务，`vad_cnn` 走 CNN 加速器 |
| **模型训练** | `model_workspace` | ai8x 训练链路：数据制备 → 归一化 → 剪枝 → 自蒸馏 → QAT → ai8xize |
| **综合能量测试** | `energy_test` / `max78000\e7_power` | UT70 电流表 + 官方 DLL 脚本化采集，1 h 实测与基线差分 |

---

## 二、软件框架

### 2.1 分层

```
01_rtos/            FreeRTOS 内核 + 官方 Demo（tickless / CLI 参考）
02_api/             MSDK 外设 API 文档与头文件（adc/i2c/i2s/dma/flc/...）
03_app/             应用工程（真正的固件在这里）
├── main.c          入口：时钟切换、Board_Init、建任务、起调度器
├── tasks_manage.c  音频采集任务 + CNN 推理任务（用户代码）
├── tasks_manage.h  任务栈/优先级/尺寸宏
├── models/
│   ├── model_common.h
│   ├── softmax.c
│   └── vad/         ★ 部署模型：vad_cnn.c / .h / _weights.h
├── FreeRTOSConfig.h
├── max78000_app.ld 链接脚本（内存布局权威）
├── project.mk      挂库 / LINKERFILE / VPATH / IPATH
└── build/          max78000.elf / .hex
cmake/              MSDK 工程编排（MsdkProject.cmake）
CMakeLists.txt      仓库级构建入口（targets: app / sentinel / firmware / app-size / app-flash）
```

### 2.2 数据流

```
I2S 32-bit 字 ──► sample>>14 ──► HPF(100 Hz, Coeff=32604)
   ──► 丢弃前 10000 样本 ──► (uint8_t)(sample*SCALE/256)
   ──► pChunkBuff[128] ──► AddTranspose ──► 128×128 帧
   ──► 逐带归一化 (mean/std over time) + roundf(xn*16.0f) 并 clip ±128
   ──► cnn_load_data ──► vad_cnn_start() ──► 等任务通知(50 ms)
   ──► margin = s0 - s1 ──► margin < 0 判为 VOICE
```

### 2.3 板上接口

| 项 | 值 |
|---|---|
| CNN 输出地址 | `0x50404000`（低 16 位 s0、次 16 位 s1） |
| KAT（官方 sample-input） | `0x000006f7` → s0 = −9，s1 = +6，**margin = −15** |
| 中断 | `VAD_CNN_ISR`，`NVIC_SetPriority(CNN_IRQn, 5)` |
| 串口 | UART0 @115200，每帧打印 `m=<margin> <VOICE/non> miss=<n>` |
| 实测帧周期 | **1019 ms**（16384 / 16 kHz = 1024 ms，偏差 0.5 %） |

---

## 三、模型训练

### 3.1 输入表示

不做 MFCC，直接把 **16384 点原始波形折叠成 128×128**：

| 项 | 值 |
|---|---|
| 采样率 | 16 kHz |
| 帧长 | 16,384 点（1.024 s） |
| 折叠形状 | `(128, 128)` —— dim0 = 块内采样位置，dim1 = 时间块 |
| 归一化 | 逐带（沿时间轴）z-score，`eps=1e-5`，torch 默认**无偏** std |
| 训练增强 | 时间平移 `np.roll(raw, k, axis=1)`，`SHIFT_BLOCKS=10` |
| 类别顺序 | `('nonvoice', 'voice')` → class0 = nonvoice |

### 3.2 数据集

`model_workspace\sentinal_dataset\dataset_processed\`（int8，已切分）
完整盘点（5.1 份语料，全部可用）
正类材料
源	条数/段	源时长	可用窗	说明
Mobvoi p（关键字）	72,264	37.94 h	157,973	2 个短语，788 说话人，1/3/5m，TV/music 0-30dB
Mobvoi n（非关键字）	214,317	224.38 h	1,262,417	内容任意（4Hz 调制 0.606 ≈ p 的 0.595 → 绝大多数是人说话）
MUSAN speech	429	60.45 h	~425,000	LibriVox + US gov，英语
RAMC	15 对话	6.45 h 语音	38,339	中文即兴对话，30 说话人
合计			~188 万窗	
负类材料
源	条数/段	源时长	可用窗	说明
UrbanSound8K	8,732	8.75 h	46,314	10 类城市/室内，含 air_conditioner / street_music
MUSAN music	671	42.6 h	~299,000	人声演唱最像语音
MUSAN noise	933	6.2 h	~43,000	风扇/机器/车辆/雨/风
ESC-50	2,000	0.57 h	2,000	50 类环境声
RAMC 间隙	15 对话	1.36 h	1,726	同录音底噪
Mobvoi n 安静尾巴	~7 万	—	~15 万	RMS < −40 dBFS 的部分
合计			~54 万窗	

| 项 | 值 |
|---|---|
| 正样本 | 105,469 帧（Mobvoi 语音） |
| 负样本 | 105,469 帧（ESC-50 非语音） |
| 训练 / 验证 / 测试 | 147,747 / 21,229 / 41,962 |
| 文件 | `pos_X.npy` / `neg_X.npy`（各 1.61 GB）、`*_pcm.npy`、`*_split.npy`、`*_meta.json`、`build_info.json` |

### 3.3 训练阶梯（E0 → E7）

| 阶段 | 内容 | 关键结果 |
|---|---|---|
| E0–E1 | 数据制备 + 基线训练 `one_base` | val AUC 0.99611 / test 0.99582 |
| E2 | 逐带归一化（per-band normalize） | 消除音量影响，增益不变性成立 |
| E3 | 未剪枝基线上板 | 板上跑通（`sen1_cnn`） |
| **E4a** | 单层敏感度扫描（18 点，5 ep） | **FPR@TPR95 无排序能力（spearman 0.008），AUC 才是可信轴** |
| **E4b** | Optuna 40 trials（目标 cycles + AUC） | Pareto 前沿 4 点，t7 = `32/24/32/16/8/16`，**10,784 B / 38,016 cyc（−67.9 %）** |
| **E4c** | 多 seed 复核 | 单 seed 无法产生工业级显著差异，按项目口径放弃 |
| **E4d** | 自蒸馏（T=3, α=0.7） | ckpt 起点 KD 比 CE **+0.00115 val AUC**（显著）；test AUC **0.99563** |
| **E5** | ShiftQAT 10 ep + `quantize.py --clip-method SCALE` | best=ep8，val 0.995262 / test 0.995422，量化损失 ≈ 0.0002 |
| **E6** | ai8xize 生成 C 模型 `vad_cnn` | 814,512 ops，权重 10,784 B（2.4 %），偏置 130 B（6.3 %） |
| **E7** | UT70 实测 1 h 平均功耗 | **67.55 mW**，基线 48.33 mW，应用增量 19~20 mW |

### 3.4 剪枝对精度的影响（最终口径）

| | 未剪枝基线 | **剪枝+蒸馏+QAT** | 差 |
|---|---|---|---|
| val AUC | 0.99611 | 0.99526 | −0.00085 |
| test AUC | 0.99582 | 0.99542 | −0.00040 |
| test FPR | 1.095 % | 1.181 % | +0.09 pp |
| 权重 | 79,392 B | **10,784 B** | **−86.4 %** |
| 硬件 ops | 3,838,512 | **814,512** | **−78.8 %** |

---

## 四、综合能量测试（E7）

### 4.1 链路

```
PC(USB-A) ──► UT70 A-IN ──► A-OUT ──A转micro-B──► MAX78000FTHR
UT70 Micro-USB HID ──► PC（ATK_UT70DLL.dll 直采，不经 GUI）
```

**关键前提已验证**：UT70 的 D+/D- 直通成立 —— FTHR 的 DAPLink 完整枚举出 4 个接口，
所以**功耗测量与串口日志可同时进行**。

### 4.2 实测结果

| 项目 | **vad 1 h** | Hello_World 基线 |
|---|---|---|
| 时长 / 样本 | 3626 s / 725,238 | 604 s / 121,158 |
| 平均电压 | 5.24778 V | 5.24761 V |
| 平均电流 | **12.872 mA** | **9.209 mA** |
| **平均功率** | **67.548 mW** | **48.325 mW** |
| 能量 | 244.94 J = **68.04 mWh** | 29.204 J = 8.112 mWh |

**交叉验证**：CSV 积分 68.038 mWh vs 表内计数 68.023 mWh → **偏差 0.02 %**。

| 差分结论 | 值 |
|---|---|
| 应用增量 ΔP（同期 600 s 窗口） | **20.45 mW（29.7 %）** |
| 固定开销（调试器 + MCU 空转 + PMIC） | 48.33 mW（70.3 %） |
| CNN 平均功率 | **3.0 µW**（占整板 **0.0045 %**） |

串口侧同步统计（1 h）：3,415 帧，判 VOICE **16 帧（0.47 %）**，margin 均值 6.98 / min −10 / max +14，miss 0。

### 4.3 结论

> **剪枝把硬件 ops 降了 78.8 %，在整板功耗上的变化量级是 1 µW 级 —— 完全不可测。**
> 真正的功耗大头是**常开的音频前端（MAX9867 codec + I2S）与逐样本 CPU 处理**，
> 不是 CNN。整板 71 % 的功耗甚至与应用无关（调试器 + MCU 空转）。

---

## 五、目录树

```
project-egde_cnn_vad\
├── 01_rtos\                        FreeRTOS 内核 + 官方 Demo
├── 02_api\                         MSDK 外设 API 文档/头文件（adc/i2c/i2s/dma/flc/...）
├── 03_app\                         ★ 应用固件（真正要烧的工程）
│   ├── models\vad\                 ★ 部署模型 vad_cnn
│   └── build\                      max78000.elf / .hex
├── cmake\                          MSDK 工程编排
├── energy_test\                    ★ E7 实测数据与报告
├── max78000\e7_power\              ★ 能量测试工具链、DLL、器件手册
│   ├── _lib\                       ATK_UT70DLL.dll
│   ├── _ref\                       手册全文（MAX20303 / FTHR / UT70 / MAX78000）
│   ├── hello_world\                基线固件工程
│   └── tool\                       采集工具与脚本
├── model_workspace\                ★ 模型侧全部工作
│   ├── sentinal_dataset\           数据集（含 dataset_processed）
│   ├── sentinal_model_train\       ai8x 训练链路（见下）
│   └── model_check\                ai8xize 输出的独立验证工程
├── CMakeLists.txt                  仓库级构建入口
├── CMakePresets.json
└── README.md                       本文件
```

`model_workspace\sentinal_model_train\` 内部：

```
ai8x-training\            上游 ai8x-training（模型/数据集/训练器）
zero_base_last\           E0/E1 基线 + 复用代码源头
one_base_prune\           E4a 敏感度扫描 / E4b Optuna / E4c 复核
one_base_distill\         E4d 自蒸馏（含 from_base 组）
one_base_withqat\         早期 QAT 试点 + _gin 复用样本
two_base\                 ★ E6 QAT + ai8xize + 板级插件生成
amplitude_probe\          增益不变性探针
amplitude_probe_norm\     归一化后的增益探针
```

---

## 六、绝对路径索引（详细文档）

> 根目录：`C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad`

### 6.1 能量测试（E7）

| 文档 / 文件 | 说明 |
|---|---|
| `C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\energy_test\E7_REPORT.md` | ★ **E7 完整报告**：链路、三组数据、差分、CNN 能量账、限定条件 |
| `…\energy_test\README.md` | 数据目录说明：链路、工具用法、CSV 列定义、已知限制 |
| `…\energy_test\analysis_run01.md` | run01 自动分析输出（分布、纹波、自相关、串口统计） |
| `…\energy_test\analyze.py` | 分析脚本（CSV + 串口日志 → 报告） |
| `…\energy_test\run01_vad_60min.csv` | vad 固件 1 h 原始数据（725,541 行，53 MB） |
| `…\energy_test\run02_hello_10min.csv` | Hello_World 基线原始数据（121,158 行） |
| `…\energy_test\serial_1h.log` | 3,415 帧 margin 原始日志 |
| `…\max78000\e7_power\tool\ut70cap.cs` | ★ 采集工具源码（C#，直连官方 DLL） |
| `…\max78000\e7_power\tool\ut70cap.exe` | 编译产物，用法 `<秒数> <csv> [采样率]` |
| `…\max78000\e7_power\tool\serial_log.ps1` | COM3 串口并发记录脚本 |
| `…\max78000\e7_power\_lib\ATK_UT70DLL.dll` | 官方上位机 DLL（x64，HID 数据流） |
| `…\max78000\e7_power\_ref\max20303.txt` | MAX20303 手册全文（fuel gauge p.62、ADC p.55、寄存器表 p.140） |
| `…\max78000\e7_power\_ref\max78000.txt` | MAX78000 手册全文（**4.02 pJ/MAC p.12**、VREGI 电流 p.9） |
| `…\max78000\e7_power\_ref\fthr.txt` | MAX78000FTHR 板级手册（PMIC/充电/电池座/调试器） |
| `…\max78000\e7_power\_ref\ut70.txt` | UT70 用户手册全文（参数 p.5、上位机 p.18-22） |
| `…\max78000\e7_power\hello_world\` | 基线固件工程（官方 Hello_World 副本，已编译） |

### 6.2 软件框架

| 文档 / 文件 | 说明 |
|---|---|
| `…\03_app\README.md` | 模板阶段说明：内存布局、FreeRTOSConfig 改动、两个原厂坑（**注意：仍写作「04_app」，目录名已改，内容为历史记录**） |
| `…\03_app\models\vad\README_PLUG.md` | ★ CNN 模型接入说明（ISR 改名、NVIC 优先级、时间变量、去掉左移） |
| `…\03_app\main.c` | 固件入口 |
| `…\03_app\tasks_manage.c` | 音频采集 + CNN 推理两个任务（应用逻辑） |
| `…\03_app\tasks_manage.h` | 任务栈/优先级/尺寸宏 |
| `…\03_app\models\vad\vad_cnn.c` / `.h` / `vad_cnn_weights.h` | ★ 部署模型（ai8xize 产物 + 板级适配） |
| `…\03_app\max78000_app.ld` | 链接脚本（内存布局权威：SRAM 130,944 B 单核 ARM 布局） |
| `…\03_app\project.mk` | 挂库 / LINKERFILE / VPATH / IPATH |
| `…\03_app\build\max78000.hex` | 烧录文件（190,992 B） |
| `…\02_api\_global_functions.md` | MSDK 全局函数索引 |
| `…\02_api\_periph_summary.md` | 外设 API 汇总 |
| `…\02_api\periph\*.md` | 分外设文档（adc / i2c / i2s / dma / flc / …） |
| `…\01_rtos\MAX78000_FreeRTOSDemo\README.md` | 官方 FreeRTOS Demo（tickless / CLI 参考） |
| `…\cmake\MsdkProject.cmake` | MSDK 工程编排实现 |
| `…\CMakeLists.txt` | 仓库级构建入口（targets: `app` / `sentinel` / `firmware` / `app-size` / `app-flash`） |

### 6.3 模型训练

| 文档 / 文件 | 说明 |
|---|---|
| `…\model_workspace\sentinal_model_train\one_base_prune\README.md` | ★ E4 剪枝复用笔记 + E4a 敏感度扫描结论 |
| `…\model_workspace\sentinal_model_train\one_base_prune\prunning.py` | E4a 单层敏感度扫描 |
| `…\model_workspace\sentinal_model_train\one_base_prune\optuna_search.py` | E4b Optuna 搜索（目标 cycles + val AUC） |
| `…\model_workspace\sentinal_model_train\one_base_prune\_verify.py` | E4c 复核 |
| `…\model_workspace\sentinal_model_train\one_base_prune\e4a_run.log` / `e4b_run.log` / `e4b_polish.log` | 各阶段完整日志 |
| `…\model_workspace\sentinal_model_train\one_base_prune\prune_e4a\results.csv` | 18 点敏感度扫描结果 |
| `…\model_workspace\sentinal_model_train\one_base_prune\prune_e4b\pareto.json` | Pareto 前沿（`study.db` 为 Optuna 数据库） |
| `…\model_workspace\sentinal_model_train\one_base_distill\distill.py` | E4d 自蒸馏（teacher 冻结，KL + CE） |
| `…\model_workspace\sentinal_model_train\one_base_distill\distill.txt` / `distill.csv` | 3 组实验对照表 |
| `…\model_workspace\sentinal_model_train\two_base\qat.py` | ★ E6 ShiftQAT（10 ep，best=ep8） |
| `…\model_workspace\sentinal_model_train\two_base\qat_run.log` | QAT 完整日志 |
| `…\model_workspace\sentinal_model_train\two_base\vad_cnn.yaml` | ai8xize 配置（双处理器掩码） |
| `…\model_workspace\sentinal_model_train\two_base\probe.py` | 整型仿真验收（3 条判据 + 增益 k 扫描） |
| `…\model_workspace\sentinal_model_train\two_base\make_plug.py` | ai8xize 输出 → 板级插件（ISR/NVIC/时间变量） |
| `…\model_workspace\sentinal_model_train\two_base\vad_cnn\log.txt` | ★ ai8xize 输出：814,512 ops / 10,784 B / 130 B |
| `…\model_workspace\sentinal_model_train\two_base\two_base_qat-q.pth.tar` | 量化权重（ai8xize 输入） |
| `…\model_workspace\sentinal_dataset\dataset_processed\build_info.json` | 数据集构建参数（WIN=16384, SR=16000, HOP=8192） |
| `…\model_workspace\sentinal_dataset\check_dataset.py` | 数据集自检 |
| `…\model_workspace\model_check\readme.md` | ai8xize 输出的独立验证工程说明 |
| `…\model_workspace\sentinal_model_train\ai8x-training\` | 上游 ai8x 训练框架（含 `distiller-repo`） |

---

## 七、从零复现

### 7.1 环境

```powershell
conda activate ai8x                       # python: C:\Users\13157\miniconda3\envs\ai8x\python.exe
$env:MAXIM_PATH = "D:/MaximSDK"           # MSDK 根
# 训练必须加 --compiler-mode none（Windows 无 triton）
```

关键约束：
- `ai8x-training` 官方锁 torch 2.3.1，但 RTX 5070 Ti（Blackwell）需要 **cu128**，故本机用 torch 2.11.0+cu128
- `quantize.py` 必须走 **根 shim**（`ai8x-synthesis\quantize.py`），直接跑 `izer\quantize.py` 会 `ImportError`

### 7.2 训练

```powershell
cd C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\model_workspace\sentinal_model_train
python one_base_prune\prunning.py                # E4a 敏感度
python one_base_prune\optuna_search.py           # E4b Optuna
python one_base_distill\distill.py               # E4d 自蒸馏
python two_base\qat.py                           # E6 QAT
```

### 7.3 量化 + 部署

```powershell
# 1) 量化（cwd 必须是 ai8x-synthesis 根）
python quantize.py --clip-method SCALE -a max78000 -c two_base_qat_best.pth.tar -r -q

# 2) ai8xize（cwd 必须是 ai8x-synthesis 根；yaml 需 processors + output_processors 两套掩码）
python ai8xize.py --device MAX78000 --config-file two_base\vad_cnn.yaml `
  --checkpoint-file two_base\two_base_qat-q.pth.tar --prefix vad_cnn `
  --test-dir two_base --sample-input <npy> --no-version-check --overwrite

# 3) 生成板级插件
python two_base\make_plug.py
```

### 7.4 编译与烧录

```powershell
$env:PATH = "D:\MaximSDK\Tools\GNUTools\xpack-arm-none-eabi-gcc-15.2.1-1.1\bin;D:\MaximSDK\Tools\MSYS2\msys64\usr\bin;" + $env:PATH
cd C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\03_app
make.exe -r -j 8 TARGET=MAX78000 BOARD=FTHR_RevA MAXIM_PATH=D:/MaximSDK
arm-none-eabi-objcopy -O ihex build\max78000.elf build\max78000.hex

# 烧录（路径必须用正斜杠，OpenOCD 的 Tcl 会吃掉反斜杠）
D:\MaximSDK\Tools\OpenOCD\xpack-openocd-0.12.0-7\bin\openocd.exe `
  -s D:/MaximSDK/Tools/OpenOCD/scripts -f interface/cmsis-dap.cfg -f target/max78000.cfg `
  -c "program C:/.../03_app/build/max78000.hex verify reset exit"
```

> `make` 默认目标**不产出 hex**，必须手动 `objcopy`。

### 7.5 功耗测量

```powershell
# 1 h 采集（200 SPS）
C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\max78000\e7_power\tool\ut70cap.exe `
  3600 C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\energy_test\run01_vad_60min.csv 200

# 分析
python C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\energy_test\analyze.py
```

---

## 八、已知限制（读数据前必看）

1. **测点是 VBUS，含板上 DAPLink 调试器**（约 40 mW 量级）。67.55 mW **不能**说成"MAX78000 的功耗"。
2. **1 h 内存在 −3.2 % 热漂移**（69.9 → 67.5 mW），跨轮对比必须用同期窗口。
3. **推理突发在电流波形上不可分辨**（表内部做时间平均），单次推理能量只能靠差分或官方 pJ/MAC 推算。
4. **FPR@TPR=95 % 不适合做剪枝排序**（E4a 实测 val/test 符号一致率仅 8/18，spearman 0.008）；**AUC 是唯一可信轴**。
5. **单 seed 无法产生工业级显著差异**，多 seed 复核已按项目口径放弃。
6. `03_app\README.md` 是模板阶段产物，里面仍写 `04_app` 与旧目录名，**内容为历史记录**，以本文件为准。
7. 根 `CMakeLists.txt` 的 target 名可能与目录名不同步；**直接进 `03_app` 用 `make` 最稳**。

---

## 九、许可与致谢

- 训练框架：[Analog Devices ai8x-training](https://github.com/analogdevicesinc/ai8x-training) / [ai8x-synthesis](https://github.com/analogdevicesinc/ai8x-synthesis)
- 数据集：Mobvoi Hotwords（正样本）、ESC-50（负样本）
- 器件资料：MAX78000 / MAX78000FTHR / MAX20303 / UT70 官方数据手册（见 `max78000\e7_power\_ref\`）
