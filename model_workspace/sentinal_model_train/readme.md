

此模型为边缘系统人声路由识别模型，小参数，需要搭配vad音量门限和数据逐带归一化一起使用
训练思路参考文章：
VAD to the Bone: Ultra-Tiny Speech Activity Detection for Edge Deployment
[kilovad](https://arxiv.org/abs/2607.25870)

**训练阶梯：**

| 阶段 | 改什么 | 依据 | 判据 |
|---|---|---|---|
## E0 | baseline，5 seeds | — | AUC + **FPR@TPR=0.95** |     完成度：100%。已获得可靠的基线模型数据与测试
[基线训练日志](./ai8x-training/logs/zero_base___2026.10.31-170625/zero_base___2026.10.31-170625.log)
总结：边缘模型应当遵循大模型剪枝调教到小模型的原则，而不是一上来就搞小模型。同时模型训练出来的loss曲线等等一定要看，必要的时刻
注意甚至先怀疑数据集的问题
基线auc见后文附


## E1 | 幅度侧信道探针（不训练）：test 波形 ×{0.125…4}，画 FPR vs 增益 | 有没有侧信道 |
把同一个测试波形，分别乘以不同的增益系数（0.125, 0.25, 0.5, 1, 2, 4），然后送进模型推理，画出 FPR vs 增益​ 的曲线。
结论：音量降到 ⅛（gain 0.125）时，误报率从 1.18% 飙到 10.4%——9 倍。
降到 1/16（0.0625）时，FPR@TPR95 到 43.7%，模型基本废了。
升到 4 倍，FPR 到 5.7%——5 倍。
平坦区只有 g ∈ [0.5, 2] 这么窄一条。连 g=2 的 +0.006 都已经是噪声地板（0.003）的 2 倍。
机制很清楚：模型在靠"响度"判断人声。 安静时，真语音的分数掉下去 → 为了保住 TPR=0.95 阈值往下压 → 安静的负样本全部涌进来 → FPR 爆炸。同时 TPR@FPR1% 从 0.94 塌到 0.58，说明安静的真语音也判不出来了。
[zero_base基线探针评估结果](./amplitude_probe/amplitude_probe.txt)
[探针代码位置](./amplitude_probe/amplitude_probe.py)


## E2 | 逐带归一化（改 `datasets/sentinel.py` transform）→ 新基线 | 归一化后曲线平坦 |
加入数据预处理策略，重训一个基线，然后进行e1探针评估
注：探针里增益 g 必须乘在原始波形上、归一化之前，因为真实部署是"音量先变了 → 前端再归一化"。如果乘在已经归一化的数据上，测的不是"音量变化对模型的影响"，而是另一个无关的东西。
换而言之，我们是在测试一种数据预处理策略对不对。
结论：归一化将高增益侧端的判断纠正了，低增益侧端仍旧有问题。
**但是极端安静没信息是int8系统的问题，不是归一化不归一化的问题，加上此模型使用的时候需要有前端vad能量判别，过低音量的信号送不进来，所以归一化通过**
边缘区：−12 dBFS（g=0.25）和 +12 dBFS（g=4）——FPR 到 ~2%，还能用，但别长期待在这。
无效区：≤ −18 dBFS（g ≤ 0.125）——FPR 从 7% 飙到 26%，模型已经废了。
VAD 门限参考设 ≥ −12 dBFS（g ≈ 0.25），这样任何过门的信号至少落在"边缘→有效"区间。
[归一化预处理加入之后训练的基线](./ai8x-training/logs/one_base___2026.11.03-182532/)
[归一化后one_base探针评估结果](./amplitude_probe_norm/amplitude_probe_norm.txt)
[新探针（在归一化之前加入信号干扰）代码位置](./amplitude_probe_norm/amplitude_probe_norm.py)



## E3 | shiftqat，测试归一化之后的基线模型能否在max78000上正常跑通,进行初步全链路测试 | 加入预处理之后的基线模型可以正常识别出人声 |
关键数字
阶段	val Top1
float 基线（one_base, ep27）	97.33
QAT 切入瞬间（ep30）	96.60（量化初始掉点，正常）
QAT 当前最优（ep42）	97.225
最近（ep45）	96.665
[基线模型qat后](./ai8x-training/logs/one_base_withqat___2026.11.04-104409/)
[编译出来的可上板引入模型](./one_base_withqat/sen1_cnn/)
另：结构性问题——**归一化放在音频任务里会丢采样**
128 列 × 3 遍 × 128 点 ≈ 4.9 万次浮点迭代 + 128 次 sqrtf，60 MHz 上估 20~50 ms。这期间 I2S FIFO 没人掏 → 下一帧前段采样丢。之后需要协调归一化与模型运转，与采样的问题。max78000之后浮点运算的问题需要协调，寻找解决办法。
修复：量化问题，按权重推导 shift会导致数据的切割过于武断，使得小信号被抹掉，改为统一采用 shift=0 + 0.85·max 权重缩放，保住信号本身，**也就是在使用quantize.py时加入--clip-method，在之后e6进行qat和量化的时候，优先排查此问题**
[本问题的详细回答与解释](./one_base_withqat/关于量化的详细解释.md)
修复量化问题之后模型上板子可以识别到人声，一旦我（实验者）说话模型数值会立刻偏向负数，换而言之，板子上面的归一化基线模型**可以直接投入使用**


## E4 | 剪枝 + 自蒸馏 + Optuna：目标 `(cycle, AUC_val)`，40 trials | 前沿 2 点满足 FPR ≤0.015 且 cycle ≤0.5×基线 |
zero_base确认了数据集范围，但是同样的其中留下了一些可以参考的，为之后剪枝自蒸馏留下了一些可以参考的代码,之后可以尝试复用
[可复用的关于剪枝与参数搜索的代码](./zero_base_last/)
结构化剪枝：先对模型每个层的部分通道大概确定模型的表现，进行剪枝，对原始基线模型每个层分别剪枝25%，50%，75%的通道数目以观测每个层对整个模型的影响。总计3*6=18个探索点。为之后optuna搜索最优参数比例先大致划定搜索范围。
② conv1 16ch 是全场唯一 val/test 同向恶化的点
conv1	val AUC	val FPR	test AUC	test FPR
48ch	+0.0000	+0.0012	+0.0004	−0.0007
32ch	−0.0001	+0.0019	+0.0008	−0.0018
16ch	−0.0018	+0.0155（×2.2）	−0.0010	+0.0087（×1.8）
18 个点中只有这一行的 val 和 test 同向恶化，因此只有它可信。zero_base 把下界定在 16 是错的；在 one_base 上这样做要付出代价。
③ zero_base 的「conv3 最划算」结论被反转
one_base 上 conv3 只砍 25%（96→72）时：val AUC −0.0018、val FPR +0.0112；砍到 24ch 时反而只 −0.0009。结果非单调，说明 72ch 那一行遇到了不利的随机种子。相反，conv2 仍是最划算的一层：砍到 24ch 省 34,560 B，AUC 只 −0.0004。
[逐层敏感度初步探测数据与过程](./one_base_prune/README.md)
**optuna路径方式**： Optuna 多目标 40 trials × 5ep/lr1e-3（后台，~4h）
[optuna过后结果模型参数(最佳)](./one_base_prune/prune_e4b/ckpts/trial_0007.pth.tar)
所有候选模型数据大小：
配置	channels	权重	文件	文件大小
t7	32/24/32/16/8/16	10,784 B	trial_0007.pth.tar	73,025 B
t37	32/36/24/16/12/16	12,096 B	trial_0037.pth.tar	78,273 B
t22	32/24/40/36/12/12	15,064 B	trial_0022.pth.tar	90,113 B  数据炼丹，名不虚传啊...
**最终结果是剪枝+自蒸馏，剪枝+微调，剪枝+微调+自蒸馏三个实验数据**
剪枝 + 自蒸馏	剪枝 + 微调	剪枝 + 微调 + 自蒸馏
起点	刚剪完（尚未训练）	刚剪完（同左）	t7 ckpt（已 5ep CE 微调）
训练	8ep，α·CE + 0.3·KL	8ep，纯 CE	5ep CE → 再 8ep α·CE + 0.3·KL
通道	32/24/32/16/8/16	32/24/32/16/8/16	32/24/32/16/8/16
权重 / cycles	10,784 B / 38,016<br>（−86.4% / −67.9%）	10,784 B / 38,016	10,784 B / 38,016
val AUC	0.99485 [0.99461, 0.99500]	0.99415 [0.99325, 0.99467]	0.99519 [0.99496, 0.99536]
val FPR@TPR95	1.71% [1.60, 1.90]	2.26% [1.98, 2.76]	1.75% [1.63, 1.86]
test AUC	0.99518 [0.99507, 0.99525]	0.99546 [0.99542, 0.99551]	0.99563 [0.99552, 0.99577]
test FPR@TPR95	1.25% [1.22, 1.28]	1.35% [1.33, 1.38]	1.14% [1.03, 1.20]
test Top1	97.34% [97.28, 97.42]	97.24% [97.14, 97.43]	97.46% [97.37, 97.57]
TPR@FPR1%	93.96% [93.94, 93.99]	93.55% [93.42, 93.67]	94.45% [94.20, 94.95]

每格为 3 个 seed 的均值 [min, max]。起点状态：刚剪完 val AUC 0.91527 / FPR 28.01% / test AUC 0.92334 / FPR 25.97% / Top1 79.66% / TPR 10.31%。


**与未剪枝基线的差（右列）**
指标	基线	剪枝+微调+自蒸馏	Δ
test AUC	0.995824	0.99563	−0.00019
test FPR@TPR95	1.095%	1.14%	+0.05 pp
test TPR@FPR1%	94.56%	94.45%	−0.11 pp
test Top1	97.50%	97.46%	−0.04 pp
val AUC	0.996105	0.99519	−0.00092
权重 / cycles	79,392 B / 118,272	10,784 B / 38,016	−86.4% / −67.9%

三句判读
① 蒸馏在“恢复”场景（左列 vs 中列）：不显著
配对差值 kd − ce（同 seed、同起点）：dAUC val +0.00071 [−0.00006, +0.00174]，均值 0.00071 < 半极差 0.0009，按判据不成立。test AUC 反而 −0.00028。
唯一站得住的是 val FPR −0.55 pp，3/3 seed 同向（1.64<1.98、1.90<2.03、1.60<2.76）。
② 蒸馏在“精修”场景（右列 vs A 的 CE 对照）：显著
配对差值：dAUC val +0.00115 [+0.00063, +0.00143]，3/3 同为正，均值 0.00115 ≈ 2.9× 半极差 → 真效应。dFPR val −0.50 pp。
机制很清楚：起点已经是 5ep CE 训过的模型，
继续 CE：0.99474 → 0.99404（−0.00070，退化）
继续 KD：0.99474 → 0.99519（+0.00045，提升）
teacher 的软标签在这里起的是正则作用，抑制了继续训练带来的过拟合。
③ 两阶段方案（右列）在 test 轴全面领先
test AUC +0.00045 over 左列、+0.00017 over 中列；test FPR 1.14%（另两列 1.25% / 1.35%）；TPR@FPR1% 94.45%（另两列 93.96% / 93.55%）。
[最终剪枝+微调+自蒸馏的模型文件,作为下一步shifitqat+量化后上板的模型](./one_base_distill/ckpts/t7_kd_s1001.pth.tar)
[剪枝+自蒸馏的模型文件（参考，不作为下一步使用）](./one_base_distill/from_base/ckpts/t7-base_kd_s1001.pth.tar)





## E5 | 对剪枝之后的模型QAT（ai8x-training 的 ShiftQAT）,然后量化,**注意之前出现的量化问题** | C1–C7 通过；AUC 掉 <0.002 |
[注意事项参见](./one_base_withqat/关于量化的注意事项.md)
[shiftqat量化结果](./two_base/two_base_qat_best.pth.tar)
QAT 结果：10 epoch，best = ep8，val AUC 0.995262 / FPR 1.913%、test AUC 0.995422 / FPR 1.181%（float 起点是 0.99536 / 0.99562，量化后分别掉 0.0001 / 0.0002





## E6 | ai8xize（写 YAML 综合），上板 | 可以直接用的c语言文件 |
[模型c语言可用文件](./two_base/vad_cnn/)
模型实际指标
sen1_cnn	vad_cnn
通道	64/96/96/64/32/16	32/24/32/16/8/16
权重	79,392 B (17.9%)	10,784 B (2.4%)，−86.4%
硬件 ops	3,838,512	814,512，−78.8%
bias	370 B (18.1%)	130 B (6.3%)
输出地址	0x50404000	0x50404000（相同）
输出解码	raw int8	完全相同，app 不用改













附：A:zero_base数据
基线auc：
ckpt	Top1	AUC	FPR@TPR=0.95	TPR@FPR=1%
best (ep22)	97.598%	0.9962	1.18%	93.88%
checkpoint (ep39)	97.738%	0.9966	0.89%	95.39%
混淆矩阵 @ argmax（scores ≥ 0）

best (ep22)

                 pred_neg  pred_pos
true_neg (21001):  20529       472
true_pos (20961):    536     20425

checkpoint (ep39)

                 pred_neg  pred_pos
true_neg (21001):  20458       543
true_pos (20961):    406     20555
混淆矩阵 @ 部署工作点（卡 TPR=0.95）

best — thr = 1.2504

                 pred_neg  pred_pos
true_neg (21001):  20753       248
true_pos (20961):   1041     19920
  TPR=0.9503  FPR=0.0118  Precision=0.9877
checkpoint — thr = 2.0358

                 pred_neg  pred_pos
true_neg (21001):  20814       187
true_pos (20961):   1043     19918
  TPR=0.9502  FPR=0.0089  Precision=0.9907



B：参考论文
| # | 论文 | 实际身份 | 你的描述 |
|---|---|---|---|
| ① | [Ultra-Low Power Keyword Spotting at the Edge](https://export.arxiv.org/abs/2111.04988) | arXiv:2111.04988，**Ulkar & Okman，ADI Istanbul** | ✅ 全对，而且比你说的更要紧 |
| ② | [ShiftQAT](https://arxiv.org/abs/2610.21695) | arXiv:2610.21695，**Buyuksolak / Okman / Ulkar，ADI** | ✅ 全对 |
| ③ | [BED: A Real-Time Object Detection System for Edge Devices](https://export.arxiv.org/abs/2202.07503) | arXiv:2202.07503，ADI + Texas A&M（含 Ulkar、Okman） | ✅ 300 KB / 91.9 ms / **1.845 mJ** |
| ④ | **LbLTT** = Layer-by-Layer Transient Toolchain | [Fine-grained Hardware Acceleration for Efficient Batteryless Intermittent Inference on the Edge](https://dl.acm.org/doi/10.1145/3608475)，**ACM TECS**，特伦托大学（**不是 ADI**） | ✅ |
| ⑤ | [DEX: Data Channel Extension](https://ar5iv.labs.arxiv.org/html/2412.06566) | arXiv:2412.06566，**Nokia Bell Labs / UNIST / Glasgow** | ✅ 而且是最有料的一篇 |