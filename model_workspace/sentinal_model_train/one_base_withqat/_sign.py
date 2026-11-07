import importlib.util, os, sys
import numpy as np, torch
TRAIN = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\ai8x-training"
LOG = os.path.join(TRAIN, r"logs\one_base_withqat___2026.11.04-104409")
DATA = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_dataset\dataset_processed"
os.chdir(TRAIN); sys.path.insert(0, TRAIN)
import ai8x
spec = importlib.util.spec_from_file_location("sm", os.path.join(TRAIN,"models","sentinel.py"))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
ai8x.set_device(85, simulate=False, round_avg=False)
m = sm.KiloVAD_MAX()
sd = torch.load(os.path.join(LOG,"one_base_best.pth.tar"), map_location="cpu", weights_only=False)["state_dict"]
m.load_state_dict({(k[7:] if k.startswith("module.") else k): v for k,v in sd.items()}); m.eval()

rng = np.random.default_rng(11)
print(f"{'sample':10s} {'logit0(non)':>11s} {'logit1(voice)':>13s} {'s0-s1':>8s}  {'truth':>6s}  verdict")
for name, tag, truth in (("pos","voice","voice"),("neg","noise","non")):
    a = np.load(os.path.join(DATA,f"{name}_X.npy"), mmap_mode="r")
    sp = np.load(os.path.join(DATA,f"{name}_split.npy"))
    idx = np.sort(rng.choice(np.flatnonzero(sp==2), size=4, replace=False))
    for j,i in enumerate(idx):
        x = np.asarray(a[i], dtype=np.float32)
        R = (x - x.mean(-1,keepdims=True))/(x.std(-1,ddof=1,keepdims=True)+1e-5)
        with torch.no_grad():
            lg = m(torch.as_tensor(R[None], dtype=torch.float32))[0]
        print(f"{tag}{j:<9d} {lg[0].item():11.2f} {lg[1].item():13.2f} {lg[0].item()-lg[1].item():8.2f}  {truth:>6s}")
