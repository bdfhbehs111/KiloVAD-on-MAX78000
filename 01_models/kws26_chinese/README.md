# 中文口令识别模型（chinese_kws）

> MAX78000 声学哨兵的**深层模型**：判断异常声"是什么"——**25 个中文命令 + 1 个其他类 = 26 类**
> 定案日期：2026-10-07

## 性能指标

| 项 | 值 |
|---|---|
| **任务** | 26 类中文口令识别（25 命令 + 其他） |
| **参数量** | **29,514**（部署，去掉蒸馏专用投影头） |
| **准确率** | **95.92%**（验证集） |
| **输入** | 折叠 PCM `(128, 128)`，`[-128, 127]`（与哨兵共前端） |
| **教师** | `microsoft/wavlm-base-plus`（蒸馏） |
| **上板** | ✅ 已生成完整 MAX78000 C 工程 |

## 目录结构

```
chinese_kws/
├── weights/                      # 模型本体
│   ├── student_kws_weights.pth.tar   PyTorch 权重（95.92%）
│   ├── kws26_ai8x.pth.tar            ai8x 格式（含量化元参数）
│   ├── kws26_ai8x_q8.pth.tar         量化后 8bit —— 上板用这个
│   └── kws_classes.json              26 类名列表
│
├── code/                         # 必要代码
│   ├── student.py                    学生模型定义（宽度可配置）
│   ├── download_syntts.py            下载 SynTTS-Commands 中文命令集
│   ├── prepare_data_kws.py           切片：SynTTS 命令 + ESC-50 负样本
│   ├── extract_teacher.py            提取 WavLM 教师 embedding
│   ├── distill_kws.py                蒸馏训练（MSE + CE）
│   └── export_ai8x_checkpoint.py     PyTorch 权重 → ai8x checkpoint
│
└── max78000/                     # 上板固件
    ├── kws26-hwc.yaml                网络描述（processors/output_processors 已调好）
    ├── sample_kws_26.npy             输入样本（128×128 int64）
    └── kws26/                        生成的完整 C 工程
        ├── weights.h  (100.2 KB)     ← 8bit 权重，烧进 flash
        ├── cnn.c / cnn.h             CNN 推理
        ├── main.c / softmax.c        主程序 + softmax
        ├── Makefile / project.mk     编译
        └── .vscode/                  调试配置
```

## 模型结构

```
输入 折叠PCM (128, 128)
  ↓ Conv1d(128→32, k=3, p=0) + ReLU              → (32, 126)
  ↓ MaxPool(2) + Conv1d(32→48, k=3, p=1) + ReLU  → (48, 63)
  ↓ MaxPool(9) + Conv1d(48→32, k=3, p=1) + ReLU  → (32, 7)
  ↓ MaxPool(7) + Conv1d(32→64, k=3, p=1) + ReLU  → (64, 1)
  ↓ 摊平 → 64 维 embedding
  ↓ Linear(64 → 26)                                → 26 类 logits
```

> **注意**：池化全部融合进 conv（时间维 128→126→63→7→1），这是为了满足
> MAX78000 "池化窗口 ≤ 16、且 YAML 中池化是 conv 属性"的约束。

## 完整流水线（从零复现）

```powershell
# 0. 环境：ai-train（训练）/ ai8x（量化上板）
# 1. 下载数据
python code/download_syntts.py

# 2. 数据准备（SynTTS 命令 → 6000×25 段 + ESC-50 负样本 6000 段）
python code/prepare_data_kws.py

# 3. 提取教师 embedding（WavLM，约 5 分钟 GPU）
python code/extract_teacher.py

# 4. 蒸馏训练（26 类，60 epochs 约 2 分钟）
python code/distill_kws.py --epochs 60 --width 32,48,32,64

# 5. 迁移成 ai8x checkpoint
python code/export_ai8x_checkpoint.py

# 6. 量化（在 ai8x-synthesis 目录）
python quantize.py weights/kws26_ai8x.pth.tar weights/kws26_ai8x_q8.pth.tar --device MAX78000 -c max78000/kws26-hwc.yaml

# 7. 生成 C 代码（在 ai8x-synthesis 目录）
python ai8xize.py --no-version-check --overwrite --test-dir <out> --prefix kws26 `
  --checkpoint-file weights/kws26_ai8x_q8.pth.tar `
  --config-file max78000/kws26-hwc.yaml --device MAX78000 `
  --sample-input max78000/sample_kws_26.npy
```

## MAX78000 关键约束（踩过的坑，别重蹈）

1. **池化窗口 ≤ 16**：`mean-pool over 30` 做不了 → 改成池化融合进 conv（pool 2/9/7，最后 T=1）。
2. **`output_width` 必须是 8 或 32**（硬件宽度，不是类别数）。
3. **`processors` = 输入通道侧**：128 输入通道 → 64 位掩码。
4. **`output_processors` = 输出通道侧**：必须显式指定（不写会继承下一层的值而报错）。
5. **最后 fc 输出 26 类 → 26 位掩码**：`0x0000000003ffffff`。
6. ai8xize 启动会联网检查版本 → 加 `--no-version-check`。
7. sample 数据必须是 **int64** 的 `(128,128)` 数组 → 用 `--sample-input` 指定。
8. ai8x-synthesis 依赖（rich/onnx/xxhash/PyGithub）需单独安装。

## 类别列表（26 类）

见 `weights/kws_classes.json`：

```
Hello_小智, 上一曲, 上一首, 下一曲, 下一首, 从头播放, 减小音量, 单曲循环,
嗨_三星小贝, 增大音量, 天猫精灵, 小度小度, 小爱同学, 小艺小艺, 拒接来电,
挂断电话, 接听电话, 播放, 播放上一张专辑, 暂停, 继续播放, 跳到第一首,
静音, 音量最大, 音量调到50%, _other_
```

## 数据来源

- **SynTTS-Commands**（25 个中文命令，TTS 合成）：[arXiv 2511.07821](https://ar5iv.labs.arxiv.org/html/2511.07821)，HuggingFace `lugan/Syntts-Commands-Media-Dataset`
- **ESC-50**（负样本 / "其他"类）：GitHub `karolpiczak/ESC-50`
