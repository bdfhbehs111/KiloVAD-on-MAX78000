# 01_models — 两个已交付的 MAX78000 模型

> 两个模型**都已训练完成、量化完成、生成完整可编译的 C 工程**，并且**各自实测编译通过**。
> 这是在 MAX78000 上做「层级唤醒」的计算内核。

---

## 一、两个模型是什么（别搞混）

| | 🛡️ **极简哨兵** | 🎯 **中文口令** |
|---|---|---|
| **角色** | **门控**：判断"环境是否异常" | **识别**：判断"是哪一条口令" |
| **做什么** | 二分类（正常 / 异常） | 26 分类 |
| **什么时候跑** | **每帧都跑**（常开，功耗敏感） | **只在哨兵判异常时跑**（按需） |
| **输入** | 折叠 PCM 128×128 int8 | 折叠 PCM 128×128 int8 |
| **参数量** | **2,003**（板上）/ 2,087（PyTorch） | **29,514** |
| **推理延迟** | **3,894 周期 ≈ 39 µs** @100 MHz | **12,204 周期 ≈ 122 µs** @100 MHz |
| **输出** | 2 个 int8，压进 1 个 uint32 | 26 个 uint32 |
| **权重内存** | 1,920 B / 442,368 B（0.4%） | 29,312 B / 442,368 B（6.6%） |
| **`weights.h`** | 10.2 KB | 100.2 KB |
| **标准工程占用** | Flash **65,024 B（12.40%）** / SRAM 5,368 B（4.10%） | Flash **94,720 B（18.07%）** / SRAM 5,368 B（4.10%） |
| **技术路线** | 手工设计 + 频率强调层（DrongoNet 思路） | **WavLM 蒸馏** → 小 CNN |
| **数据集** | ESC-50（16 正常类 / 8 异常类） | SynTTS-Commands 25 条中文口令 + `_other_` |
| **目录名** | `sentinel_gate_bin2/` | `kws26_chinese/` |

> 命名说明：目录名里带了**角色 + 配置**，避免以后拿混。
> `sentinel_gate_bin2` = 哨兵 / 门控 / 二分类；
> `kws26_chinese` = 关键字识别 / 26 类 / 中文。

---

## 二、每个包里的目录结构（两边一致）

```
<模型名>/
├── README.md           该模型的完整规格、参数扫描、硬件约束
├── code/               训练与导出脚本（Python）
│   ├── ...             数据准备 / 训练 / 蒸馏 / 导出
├── weights/            各阶段权重
│   ├── *_b2087.pth.tar       PyTorch 原始权重（哨兵）
│   ├── student_*_weights.*   PyTorch 学生权重（口令）
│   ├── *_ai8x.pth.tar        ai8x 格式（可训练/量化）
│   ├── *_ai8x_q8.pth.tar     ⭐ 8-bit 量化后（喂给 ai8xize 的就是这个）
│   └── kws_classes.json      26 类标签表（口令专用）
└── max78000/           ai8xize 生成的板上工程
    ├── *-hwc.yaml           网络描述（层配置 + 内存掩码）
    ├── sample_*.npy         int64 (128,128) 示例输入
    └── <项目名>/            ⭐ 完整 C 工程（可直接 make）
        ├── cnn.c / cnn.h        CNN 驱动（含 unload）
        ├── weights.h            量化权重（C 数组）
        ├── main.c               已知答案自测 main
        ├── softmax.c            定点 softmax
        ├── sampledata.h         示例输入（测试用）
        ├── Makefile / project.mk
        └── .vscode / .settings  IDE 配置
```

---

## 三、单独编译验证

每个包里的 C 工程都是**独立可编译**的（不带 FreeRTOS，纯裸机已知答案自测）：

```powershell
D:\MaximSDK\setenv.bat
cd <本目录>\sentinel_gate_bin2\max78000\sentinel      # 或 kws26_chinese\max78000\kws26
make -r -j 8 TARGET=MAX78000 BOARD=EvKit_V1 MAXIM_PATH=D:/MaximSDK
```

或用顶层 CMake：

```powershell
cmake --build build --target sentinel     # 哨兵
cmake --build build --target kws26        # 中文口令
cmake --build build --target sentinel-size
```

两者都会打印 `*** PASS ***`（把示例输入跑一遍，跟 ai8xize 记录的期望输出逐字节比对）。

---

## 四、前端：折叠 PCM（**不用 FFT**）

两个模型共用同一套前处理，**刻意避开了硬件 FFT**：

```
麦克风 → I2S/DMA → PCM 16 kHz
      → 取 16384 点
      → 8-bit 量化  (x/32768 + 1) * 128  →  [0,256) → 减 128 → [-128,127]
      → reshape(128,128) 后转置
      → 128×128 int8 张量  → CNN
```

要点：
- **16384 = 128 × 128**，一维 PCM 直接折叠成二维，不经过任何频域变换。
- 量化方式必须**逐位对齐训练侧**（`quantize_audio` + `__reshape_audio`，见各包 `code/`）。
- 板上实现见 `04_app/app_tasks.c` 的 `vTaskPreprocess`。

> 为什么不用 mel/FFT：MAX78000 没有硬件 FFT，软件 FFT 在 M4F 上开销大且要额外 RAM。
> 折叠 PCM 把"时域结构"直接交给 CNN，实测两个模型都够用。

---

## 四之二、⭐ 数据位宽（**写板上代码前必看**）

从 `*-hwc.yaml`、`weights.h`、训练脚本三处交叉核对的结果：

| | 🛡️ 哨兵 | 🎯 中文口令 | 依据 |
|---|---|---|---|
| **输入** | **8-bit** int8 `[-128,127]` | **8-bit** int8 `[-128,127]` | `to_folded()`：`clip(round((x+1)*128), 0, 255) - 128` |
| **权重** | **8-bit** | **8-bit** | `weights.h` 里 **4 个 int8 打包进 1 个 uint32**；拆包后范围 `[-106,116]` / `[-102,53]`，全在 int8 内 |
| **偏置** | **8-bit** | **8-bit** | 拆出 **38 B / 202 B**，与 ai8xize 报告的 bias memory **逐字节吻合** |
| **输出** | ⚠ **8-bit** | ⚠ **32-bit** | yaml 末层 `output_width: 8` vs `output_width: 32` |

权重文件用的是 `*_ai8x_q8.pth.tar`（`q8` = 8-bit 量化）。

### ⚠ 输出位宽不同 → 两个模型的**后处理不能共用**

```c
/* 哨兵：8-bit 输出，2 个类压进 1 个 uint32 */
uint32_t sen_out[1];
int8_t logit0 = (int8_t)(sen_out[0] & 0xff);
int8_t logit1 = (int8_t)((sen_out[0] >> 8) & 0xff);
/* 原始 logit（例如 -5 / 24）。ai8xize 日志明确写
   "all output scales are zero" → 没有额外缩放，直接比较或转 float 即可 */

/* 口令：32-bit 输出，26 个类各占 1 个 uint32（Q17.14 定点）*/
uint32_t kws_out[26];
softmax_q17p14_q15(kws_out, 26, probs);   /* 这才是生成 softmax.c 的用途 */
```

`04_app/app_config.h` 里的 `APP_SEN_OUT_WORDS 1` / `APP_KWS_OUT_WORDS 26`
就是按这个定的；两个 `*_cnn_unload()` 也各自处理好了字节拆分。

### ⚠ 已知缺陷：哨兵的样例输入是"退化"的

```
sentinel  sample_sentinel.npy  (128,128)  取值数 = 2    范围 [-1, 0]    ⚠
kws26     sample_kws_26.npy    (128,128)  取值数 = 102  范围 [-40, 61]  ✓
```

哨兵样例**只有 -1 和 0**（相当于近乎全静音的输入）。它仍能通过已知答案自测
（ai8xize 记录的就是该输入对应的期望输出），但**几乎没覆盖权重空间**，
自测强度很低。

**修法**：从一段真实音频重生成 `sample_sentinel.npy`，带 `--sample-input` 重跑
`ai8xize.py`（会重新生成 `sentinel/` 整个 C 工程）。

---

## 五、两个模型**不能**直接放进同一个工程

ai8xize 给两个模型生成的 `cnn.c` / `cnn.h` 里，符号**完全同名**：

```
cnn_enable  cnn_init  cnn_configure  cnn_load_weights  ...  cnn_time
CNN_ISR     CNN_OK    CNN_FAIL       CNN_NUM_OUTPUTS   ← 一边是 1，一边是 26！
memcpy32
```

**这是把它们级联起来时第一个会撞上的墙。**

已解决：`04_app/tools/namespace_models.py` 把它们改名为 `sen_*` / `kws_*`，
合并进 `04_app/models/`，并验证了最终固件里两者共存无冲突。
详见 [`../04_app/README.md`](../04_app/README.md) 第四节。

> ⚠ 本目录里的两个包保持**原名原样**，因为它们各自要能独立编译做已知答案测试。
> 只有 `04_app/models/` 里的是改名后的合并版。

---

## 六、以后要重新训练时

| 想要什么 | 改哪里 |
|---|---|
| 换异常检测的判据 | 哨兵：`sentinel_gate_bin2/code/tiny_sentinel.py`（含参数扫描） |
| 换口令词表 | 口令：`kws26_chinese/code/download_syntts.py` + `prepare_data_kws.py` |
| 换教师模型 / 蒸馏策略 | 口令：`kws26_chinese/code/extract_teacher.py` + `distill_kws.py` |
| 换网络结构 / 层配置 | 两个 `code/*.py` 里的模型定义 + `max78000/*-hwc.yaml` |
| 重跑量化 + 生成 C 工程 | 见根目录 [`../进展总结.md`](../进展总结.md) 第五节的 7 步流水线 |

**硬件约束（改结构前必读）**：池化核 ≤ 16、不支持 depthwise、INT8 下不用 BatchNorm、
`processors`/`output_processors` 掩码要对齐、`output_width` 只能是 8 或 32。
完整 30 条踩坑记录见 [`../进展总结.md`](../进展总结.md) 第六节。

---

## 七、当前局限

| 项 | 状态 |
|---|---|
| 哨兵在**真实宿舍环境**的表现 | ⬜ 未验证（ESC-50 上是 80.4% 二分类准确率；判别力比值 5.19） |
| 口令在**真人语音**上的表现 | ⬜ 未验证（合成语音测试集上 26 类 95.92%） |
| 级联端到端联调 | ⬜ 未做（骨架在 `04_app`） |
| 质心/阈值标定 | ⬜ 需按实际部署环境重算（换环境只重算质心，不用重训模型） |
