import importlib.util, os, sys
import numpy as np, torch
TRAIN = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\ai8x-training"
LOG = os.path.join(TRAIN, r"logs\one_base_withqat___2026.11.04-104409")
os.chdir(TRAIN); sys.path.insert(0, TRAIN)
import ai8x
spec = importlib.util.spec_from_file_location("sm", os.path.join(TRAIN, "models", "sentinel.py"))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
ck = torch.load(os.path.join(LOG, "one_base_qat_best-q.pth.tar"), map_location="cpu", weights_only=False)
sd = {(k[7:] if k.startswith("module.") else k): v for k, v in ck["state_dict"].items()}

ai8x.set_device(85, simulate=True, round_avg=False)
m = sm.KiloVAD_MAX(); m.load_state_dict(sd); m.eval()
print("dev flags:", ai8x.dev.DATA_BITS, ai8x.dev.ACTIVATION_BITS, ai8x.dev.FULL_ACC_BITS, ai8x.dev.WIDE_LAYER_RESOLUTION_BITS)
for n in ["conv1","conv2","conv6","fc"]:
    mod = getattr(m, n)
    print(f"  {n}: out_shift={mod.output_shift.item():.1f} thr={mod.activation_threshold.item():.1f} "
          f"final_scale={mod.final_scale.item():.1f} wide={mod.wide} wbits={mod.weight_bits.item():.0f} "
          f"w.range=[{mod.op.weight.min():.2f},{mod.op.weight.max():.2f}]")

rng = np.random.default_rng(0)
X = rng.standard_normal((8,128,128)).astype(np.float32) * 1.0
for k in (1, 8):
    x = torch.as_tensor(np.clip(np.round(X*k),-128,127), dtype=torch.float32)
    acts = {}
    hs = []
    for n in ["conv1","conv2","conv3","conv4","conv5","conv6","fc"]:
        hs.append(getattr(m, n).register_forward_hook(lambda mod, i, o, n=n: acts.__setitem__(n, o.detach())))
    with torch.no_grad(): out = m(x)
    for h in hs: h.remove()
    print(f"\n--- k={k} ---")
    for n in ["conv1","conv2","conv3","conv4","conv5","conv6","fc"]:
        a = acts[n]
        print(f"  {n:6s} shape={tuple(a.shape)} min={a.min():10.2f} max={a.max():10.2f} "
              f"mean={a.mean():9.3f} uniq={len(torch.unique(a)):5d}")
    print(f"  logits={out[0].tolist()}")
