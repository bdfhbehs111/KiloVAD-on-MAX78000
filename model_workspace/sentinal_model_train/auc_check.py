import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score, roc_curve, confusion_matrix
from torch.utils.data import DataLoader

BASE_DIR = Path(__file__).resolve().parent
AI8X_TRAINING_DIR = BASE_DIR / "ai8x-training"
sys.path.insert(0, str(AI8X_TRAINING_DIR))

import ai8x          # 必须在 sys.path.insert 之后
from models.sentinel import KiloVAD_MAX
from datasets.sentinel import sentinel_get_datasets

# simulate=False -> 纯 float，量化模块只做直通。训练时也是 simulate=False（日志第 2 行），
# 所以这是"理论上限"，两边口径一致。QAT 之后再改成 True 看定点掉点。
ai8x.set_device(85, simulate=False, round_avg=False)

LOG_DIR = AI8X_TRAINING_DIR / "logs" / "zero_base___2026.10.31-170625"
# 两个都评：best 是 epoch 22（val 选出来的），checkpoint 是 epoch 38（最后一轮）
CKPTS = ["zero_base_best.pth.tar", "zero_base_checkpoint.pth.tar"]
BATCH = 64


def pick_points(fpr, tpr):
    """按"满足约束里最严"的规则取工作点，而不是取离目标最近的点。"""
    ok = tpr >= 0.95                       # FPR@TPR=0.95: tpr>=0.95 里最小的 fpr
    fpr_at = float(fpr[ok].min()) if ok.any() else float("nan")
    ok = fpr <= 0.01                       # TPR@FPR=1%: fpr<=0.01 里最大的 tpr
    tpr_at = float(tpr[ok].max()) if ok.any() else float("nan")
    return fpr_at, tpr_at


def main():
    _, test_dataset = sentinel_get_datasets(data=None, load_train=False, load_test=True)
    labels_true = test_dataset.targets
    print(f'test 集大小: {len(test_dataset)}')
    print(f'正样本数: {int(labels_true.sum())}')
    print(f'负样本数: {int((1 - labels_true).sum())}')

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH,
        shuffle=False,      # 评估不打乱
        num_workers=0,      # Windows 下 0 最稳
    )

    results = {}

    for ckpt_name in CKPTS:
        path = LOG_DIR / ckpt_name
        checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        state_dict = checkpoint['state_dict']

        # ai8x 的 FusedConv1dReLU 把真正的卷积包在 self.op 里，所以 bias 的 key 是
        # "conv1.op.bias" 而不是 "conv1.bias"。从 state_dict 反推，比手写稳。
        use_bias = 'conv1.op.bias' in state_dict

        model = KiloVAD_MAX(
            channels=(64, 96, 96, 64, 32, 16),
            num_classes=2,
            num_channels=128,
            bias=use_bias,
        )
        model.load_state_dict(state_dict)
        model.eval()
        model = model.to('cpu')

        # 训练日志里的 "Params" 来自 distiller.model_params_stats(param_dims=[2,3,4])，
        # 只数 2/3/4 维权重张量 = 纯权重元素数（= int8 权重字节数），不含 bias 和量化标量。
        n_weights = sum(v.numel() for k, v in state_dict.items() if v.dim() in (2, 3, 4))
        n_total = sum(v.numel() for v in state_dict.values())
        print(f'\n=== {ckpt_name}   epoch={checkpoint.get("epoch")}   '
              f'bias={use_bias}   weights={n_weights} B   (state_dict numel={n_total})')

        all_logits = []
        all_labels = []
        with torch.no_grad():
            for inputs, labels in test_loader:
                all_logits.append(model(inputs))     # [batch, 2]
                all_labels.append(labels)

        logits = torch.cat(all_logits, dim=0).numpy()
        labels = torch.cat(all_labels, dim=0).numpy()

        # 关键：这是一张没有 softmax 的网络，logit 可以带任意公共偏移，
        # 所以"人声得分"必须是 log-odds = logit1 - logit0，
        # 它才和 softmax(p1) 单调等价，决策边界也才是 0（不是 0.5，也不是裸 logit1）。
        scores = logits[:, 1] - logits[:, 0]
        preds = logits.argmax(axis=1)                # 等价 scores >= 0，和训练日志 Top1 同口径

        top1 = (preds == labels).mean() * 100
        auc = roc_auc_score(labels, scores)
        fpr, tpr, thresholds = roc_curve(labels, scores)
        fpr_at, tpr_at = pick_points(fpr, tpr)

        print(f'    Top1            : {top1:.3f}%')
        print(f'    AUC             : {auc:.4f}')
        print(f'    FPR @ TPR=0.95  : {fpr_at:.4f}   ({fpr_at*100:.2f}%)')
        print(f'    TPR @ FPR=1%    : {tpr_at:.4f}   ({tpr_at*100:.2f}%)')

        cm = confusion_matrix(labels, preds, labels=[0, 1])
        print(f'    混淆矩阵 @ argmax (scores >= 0):')
        print(f'                     pred_neg  pred_pos')
        print(f'        true_neg  :  {cm[0,0]:7d}  {cm[0,1]:8d}')
        print(f'        true_pos  :  {cm[1,0]:7d}  {cm[1,1]:8d}')

        # 部署工作点：卡 TPR>=0.95 时真实的混淆矩阵（这才是板上跑的数）。
        # thresholds 是随 index 递减的，tpr>=0.95 的"第一个"索引对应最高阈值 = 最小 FPR，
        # 也就是上面 pick_points() 里 fpr[ok].min() 取到的那个点。
        thr = thresholds[np.where(tpr >= 0.95)[0][0]]
        preds95 = (scores >= thr).astype(int)
        cm95 = confusion_matrix(labels, preds95, labels=[0, 1])
        tn, fp, fn, tp = cm95.ravel()
        print(f'    混淆矩阵 @ thr={thr:.4f} (TPR=0.95):')
        print(f'                     pred_neg  pred_pos')
        print(f'        true_neg  :  {tn:7d}  {fp:8d}')
        print(f'        true_pos  :  {fn:7d}  {tp:8d}')
        print(f'        -> TPR={tp/(tp+fn):.4f}  FPR={fp/(fp+tn):.4f}  '
              f'Precision={tp/(tp+fp):.4f}')

        results[ckpt_name] = dict(top1=top1, auc=auc, fpr_at=fpr_at, tpr_at=tpr_at)

    print('\n=== 汇总 ===')
    print(f'{"ckpt":34s} {"Top1%":>8s} {"AUC":>8s} {"FPR@TPR95":>11s} {"TPR@FPR1%":>11s}')
    for name, r in results.items():
        print(f'{name:34s} {r["top1"]:8.3f} {r["auc"]:8.4f} '
              f'{r["fpr_at"]:11.4f} {r["tpr_at"]:11.4f}')


if __name__ == "__main__":
    main()
