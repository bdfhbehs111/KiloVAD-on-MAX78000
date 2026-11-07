"""Verify apply_scales (the QAT crash site) now runs on torch 2.11 after the .meta fix."""
import sys, os
train_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai8x-training')
sys.path.insert(0, train_dir)

import torch
import ai8x
ai8x.set_device(85, simulate=True, round_avg=False)
from models.sentinel import KiloVAD_MAX

model = KiloVAD_MAX()
model.eval()

# apply_scales is what crashed with KeyError: 'meta'
ai8x.apply_scales(model)
print('apply_scales OK')

# Also exercise initiate_qat (the follow-on step) to make sure no other latent crash
ai8x.initiate_qat(model, {'weight_bits': 8, 'shift_quantile': 1.0})
print('initiate_qat OK')

# A forward pass in QAT mode to make sure the quantized graph runs
x = torch.randn(1, 128, 128)
y = model(x)
print('forward OK, out shape', tuple(y.shape))
