# sys_agent_max78000 — MAX78000 层级唤醒系统总目录

> **一句话**：把「超低功耗哨兵常开门控 → 异常才唤醒深层识别」这套层级唤醒架构，
> 在 **MAX78000** 上做成可编译、可上板的实物。
>
> **本目录是下一步「RTOS 多任务调度」的地基**：模型已合并验证、RTOS 范例与内核齐备、
> 全部外设 API 可查表、应用骨架能编译。

---

## 一、四个部分

| 目录 | 内容 | 状态 |
|---|---|---|
| [`01_models/`](01_models/README.md) | **两个已交付模型**：极简哨兵（2,003 参数）+ 中文口令（29,514 参数），各含完整可编译 C 工程 | ✅ 均可编译，工程单独实测通过 |
| [`02_rtos/`](02_rtos/README.md) | **FreeRTOS V10.5.1 在 MAX78000 上的实现案例**（官方 FreeRTOSDemo 全量 + 内核源码 + 移植导读） | ✅ 可编译 |
| [`03_api/`](03_api/README.md) | **MAX78000 全部外设标准库 API 查表**（31 个头文件 → 545 个函数 / 19 个结构体 / 65 个枚举，自动生成） | ✅ 生成脚本可重跑 |
| [`04_app/`](04_app/README.md) | ⭐ **RTOS 多任务应用骨架**：9 个任务 + 同步对象 + **两个模型合并改名并验证共存** | ✅ 零警告编译通过，任务逻辑待填 |
| `cmake/` + `CMakeLists.txt` | **全目录编译统筹**：一条命令编全部或单个工程 | ✅ 四个工程全部实测编译通过 |

---

## 二、快速开始

```powershell
cd <本目录>

# 配置（默认 MAXIM_PATH=D:/MaximSDK）
cmake -S . -B build -G Ninja
cmake --build build --target list-targets    # 看所有可用目标

# 编单个工程
cmake --build build --target app             # ⭐ RTOS 应用（主力）
cmake --build build --target sentinel        # 哨兵独立验证工程
cmake --build build --target kws26           # 中文口令独立验证工程
cmake --build build --target rtosdemo        # 官方 FreeRTOS 范例

# 编全部（串行，约 2~3 分钟）
cmake --build build --target firmware

# 看占用 / 清理
cmake --build build --target app-size
cmake --build build --target clean-all
```

**不装 CMake 也能编**（直接用 MSDK 的 Makefile）：

```powershell
D:\MaximSDK\setenv.bat
cd 04_app
make -r -j 8 TARGET=MAX78000 BOARD=FTHR_RevA MAXIM_PATH=D:/MaximSDK
```

> ⚠ **别同时编多个工程**：MSDK 把外设驱动编成全工程共享的
> `Libraries/PeriphDrivers/bin/<芯片>/*.a`，并行会互相踩，
> 表现为随机 `Error 1` 且看不到任何编译错误。
> 所以 `firmware` 目标内部是串行的。

---

## 三、实测数据总表

### 编译产物（本机实测，arm-none-eabi-gcc 15.2.1）

| 工程 | 板子 | Flash | SRAM | 说明 |
|---|---|---:|---:|---|
| `sentinel` | EvKit_V1 | **65,024 B（12.40%）** | 5,368 B（4.10%） | 哨兵 + 已知答案自测 |
| `kws26` | EvKit_V1 | **94,720 B（18.07%）** | 5,368 B（4.10%） | 口令 + 已知答案自测 |
| `rtosdemo` | EvKit_V1 | 67,328 B（12.84%） | 31,320 B（23.92%） | 官方 FreeRTOS 范例 |
| ⭐ `app` | FTHR_RevA | **90,624 B（17.29%）** | **63,068 B（48.16%）** | **两个模型合并 + 9 任务骨架** |

> MAX78000 资源：**Flash 512 KB**、**SRAM 128 KB**（130,944 B）、双核共享 128 B。
> CNN 加速器另有**独立 442 KB 权重内存，不占 SRAM**。

### 模型性能（ai8xize 报告，权威）

| 指标 | 🛡️ 极简哨兵 | 🎯 中文口令 |
|---|---|---|
| 参数量 | 2,003 | 29,514 |
| **推理延迟** | **3,894 周期 ≈ 39 µs** @100 MHz | **12,204 周期 ≈ 122 µs** @100 MHz |
| 硬件算子 | 162,848 ops | 1,893,280 ops |
| 权重内存 | 1,920 B（0.4%） | 29,312 B（6.6%） |
| 输出 | 2 类 | 26 类 |
| 准确率 | 80.4%（ESC-50 二分类） | 95.92%（26 类合成语音） |
| 判别力比值 | 5.19（基线宿舍录音） | — |

> 💡 两个模型加起来每帧只占 CNN **约 161 µs**，而一帧音频是 1.024 s。
> **CNN 完全不是瓶颈** —— 可以放心把滑窗步长调小来降低检测延迟。

---

## 四、架构

```
                     ┌──────────── 常开，功耗敏感 ────────────┐
  麦克风 ─I2S/DMA─▶ 折叠PCM 128×128 int8 ─▶ 🛡️ 哨兵(2,003) ─▶ 质心/阈值判据
                     └───────────────────────────────────────┘
                                                    │
                                       正常 ────────┴──────── 异常
                                        │                      │
                                     丢弃/缓存          🎯 中文口令(29,514) 26 类
                                                               │
                                                          softmax ─▶ 串口上报 Jetson
```

**硬件分工**：ARM Cortex-M4F（100 MHz）跑全部逻辑 + FreeRTOS；CNN 加速器跑推理；
RISC-V 核预留（MSDK 的 FreeRTOS 构建只支持 M4F）。

9 个任务的划分、同步关系、数据流见 [`04_app/README.md`](04_app/README.md) 第六节。

---

## 五、⚠ 已知缺口：烧录

**本机 OpenOCD 不支持 MAX78000**，`*-flash` 目标暂时用不了。已核实：

| 检查项 | 结果 |
|---|---|
| `D:\MaximSDK\Tools\OpenOCD\scripts`（官方 `flash.mk` 期望的路径） | ❌ 不存在 |
| xpack OpenOCD 自带的 `scripts/target/max78000.cfg` | ❌ 没有（只有 max32620/25/3x/70/72/75/80/90） |
| 全套 SDK 里搜 `max78000.cfg` | ❌ 无 |

**解决办法**：装 ADI 官方 MSDK 发行版自带的 OpenOCD（它带 `max78000.cfg`），
或从 MSDK 仓库取该文件放到 `scripts/target/` 下，然后：

```powershell
cmake --build build --target app-flash
```

> 我**没有伪造** `max78000.cfg`。Flash 控制器配置写错可能损坏芯片，
> 而这台机器上无法上硬件验证——宁可不给，也不给错的。

**临时替代**：用 .bin/.hex + 其他烧录工具（J-Link、MAX78000 的 ROM 引导）烧写。
工程的 `.vscode/flash.gdb` 里有官方 GDB 烧录脚本可供参考。

---

## 六、硬件约束速查（动手前扫一眼）

| 约束 | 值 / 说明 |
|---|---|
| 主频 | 上电 **ISO 60 MHz**；显式选 IPO 后 **100 MHz**（`MXC_SYS_Clock_Select(MXC_SYS_CLOCK_IPO)`） |
| SRAM | 128 KB —— **音频环形缓冲 + 帧缓冲池会吃掉大半**，算清再动手 |
| FreeRTOS 堆 | 默认 26 KB（`configTOTAL_HEAP_SIZE`），本项目改 24 KB |
| CNN 加速器 | **单实例，必须互斥**；两模型切换要重新 `load_weights()` + `configure()` |
| CNN 池化核 | ≤ 16 |
| CNN 不支持 | depthwise（要 MAX78002）、INT8 下的 BatchNorm、硬件 FFT |
| 中断优先级 | 要调 FreeRTOS API 的 ISR，NVIC 优先级**数值必须 ≥ 5** |
| `output_width` | 只能是 8 或 32 |
| ai8xize 掩码 | `processors` = 输入侧，`output_processors` = 输出侧，**都要显式写** |

30 条完整踩坑记录（环境 / 加载推理 / 硬件约束 / 工程流程）见
[`../进展总结.md`](../进展总结.md) 第六节。

---

## 七、相关文档

| 文档 | 内容 |
|---|---|
| [`../进展总结.md`](../进展总结.md) | ⭐ **项目总文档**：目标、技术链路、30 条踩坑、下一步 |
| [`01_models/README.md`](01_models/README.md) | 两个模型的规格与用法 |
| [`02_rtos/README.md`](02_rtos/README.md) | FreeRTOS 移植导读、配置逐项解读、8→9 任务映射 |
| [`03_api/README.md`](03_api/README.md) | 外设 API 三种查法 + 10 段典型调用序列（抄自官方示例） |
| [`04_app/README.md`](04_app/README.md) | 应用骨架、模型合并方案、SRAM 账、填充顺序 |

---

## 八、下一步

1. **填任务逻辑**（顺序见 `04_app/README.md` 第七节）：
   采集 → 前处理 → 哨兵 → 门控 → 深层 → 结果 → 串口 → 缓存/监控。
2. **接上低功耗**：打开 tickless idle（照抄 `02_rtos/.../freertos_tickless.c`），
   实测空载电流。
3. **真实环境标定**：用现场录音重算门控阈值 / 质心基线。
4. **定 Jetson 协议**：UART 帧格式 + 阈值/质心下发命令。
5. **解决烧录**：拿到 `max78000.cfg` 后上板跑已知答案测试。
