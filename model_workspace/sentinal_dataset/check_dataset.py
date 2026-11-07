import os
import sys

sys.path.insert(0, os.getcwd())   # 必须在 ai8x-training 目录下运行

import numpy as np
import torch
from distiller.apputils import get_data_loaders
import datasets.sentinel as S

POS, NEG = S.POS_DIR, S.NEG_DIR

pos_X = np.load(POS + r'\mobvoi_X.npy')
neg_X = np.load(NEG + r'\esc_X.npy')
pos_group = np.load(POS + r'\mobvoi_group.npy')
neg_group = np.load(NEG + r'\esc_group.npy')

fails = []


def chk(name, cond, detail=''):
    print(('PASS  ' if cond else 'FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not cond:
        fails.append(name)


tr_ds, te_ds = S.sentinel_get_datasets(None)

chk('len(train+val) == 3468', len(tr_ds) == 3468, len(tr_ds))
chk('len(test) == 1132', len(te_ds) == 1132, len(te_ds))
chk('valid_indices == range(2764,3468)',
    list(tr_ds.valid_indices) == list(range(2764, 3468)),
    (tr_ds.valid_indices.start, tr_ds.valid_indices.stop))

# 用 .targets 属性（已按 indices 切片）
t = tr_ds.targets
chk('train  block: pos=1564', int(t[:2764].sum()) == 1564, int(t[:2764].sum()))
chk('train  block: neg=1200', len(t[:2764]) - int(t[:2764].sum()) == 1200)
chk('val    block: pos=304', int(t[2764:].sum()) == 304, int(t[2764:].sum()))
chk('val    block: neg=400', len(t[2764:]) - int(t[2764:].sum()) == 400)

ft = te_ds.targets
chk('test        : pos=732 / neg=400',
    int(ft.sum()) == 732 and len(ft) - int(ft.sum()) == 400,
    (int(ft.sum()), len(ft) - int(ft.sum())))

# ---- 逐元素精确比对 ----
X_all = S._cache['X']
split_all = S._cache['split']

x0, y0 = te_ds[0]
ref = pos_X[np.flatnonzero(split_all == 2)[0]].astype(np.float32)
chk('test[0]  dtype/shape', x0.dtype == torch.float32 and tuple(x0.shape) == (128, 128),
    (x0.dtype, tuple(x0.shape)))
chk('test[0]  values EXACT', bool(np.array_equal(x0.numpy(), ref)),
    float(np.abs(x0.numpy() - ref).max()))
chk('test[0]  target == 1', y0 == 1, y0)

# 关掉增强后，train[0] 必须和原始 npy 逐元素相等
tr_ds.n_augment = 0
xp, yp = tr_ds[0]
chk('train[0] EXACT vs mobvoi_X[0]',
    bool(np.array_equal(xp.numpy(), pos_X[tr_ds.indices[0]].astype(np.float32))),
    float(np.abs(xp.numpy() - pos_X[tr_ds.indices[0]].astype(np.float32)).max()))

# 验证块在增强开启时也必须保持原样
tr_ds.n_augment = 2764
a, _ = tr_ds[2764]
b, _ = tr_ds[2764]
refv = X_all[tr_ds.indices[2764]].astype(np.float32)
chk('val item stable under augmentation',
    bool(np.array_equal(a.numpy(), b.numpy())) and bool(np.array_equal(a.numpy(), refv)))

# 增强确实生效
raw0 = X_all[tr_ds.indices[0]].astype(np.float32)
diff = sum(0 if np.array_equal(tr_ds[0][0].numpy(), raw0) else 1 for _ in range(100))
chk('train augmentation active', 50 < diff <= 100, f'{diff}/100 rolled')

# group
chk('group: pos/neg disjoint (offset works)',
    len(set(pos_group.tolist()) & set((neg_group + 100000).tolist())) == 0)
chk('group length 4600', len(S._cache['group']) == 4600)

# ---- 走 ai8x 真实路径 ----
tl, vl, tel, ishape, _ = get_data_loaders(
    S.sentinel_get_datasets, (None, None), batch_size=32, num_workers=0,
    validation_split=0.1, deterministic=False,
    effective_train_size=1., effective_valid_size=1., effective_test_size=1.,
    test_only=False, collate_fn=None, cpu=True)

chk('ai8x input_shape == (1,128,128)', tuple(ishape[1:]) == (128, 128) and ishape[0] == 1,
    tuple(ishape))
chk('ai8x train len == 2764', len(tl.sampler) == 2764, len(tl.sampler))
chk('ai8x val   len == 704  (NOT 346)', len(vl.sampler) == 704, len(vl.sampler))
chk('ai8x test  len == 1132', len(tel.sampler) == 1132, len(tel.sampler))

xb, yb = next(iter(tl))
chk('batch shape (32,128,128)', tuple(xb.shape) == (32, 128, 128), tuple(xb.shape))
chk('batch dtype float32', xb.dtype == torch.float32, xb.dtype)
chk('batch values in [-128,127]', float(xb.min()) >= -128 and float(xb.max()) <= 127,
    (float(xb.min()), float(xb.max())))
chk('batch target is long/int', yb.dtype in (torch.int64, torch.int32, torch.int8), yb.dtype)

print()
print('FAILED:', fails if fails else 'none')
