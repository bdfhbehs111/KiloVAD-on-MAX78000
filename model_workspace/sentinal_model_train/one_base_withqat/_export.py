import numpy as np, os, json
DATA = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_dataset\dataset_processed"
OUT  = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
os.makedirs(OUT, exist_ok=True)

def ref_of(name, i):
    m = np.load(os.path.join(DATA, f"{name}_X.npy"), mmap_mode="r")
    x = np.asarray(m[i], dtype=np.float32)
    mu = x.mean(axis=-1, keepdims=True)
    sd = x.std(axis=-1, ddof=1, keepdims=True)
    return (x - mu) / (sd + 1e-5)

for name, tag, idxs in (("pos", "voice", [0, 1, 2]), ("neg", "noise", [0])):
    for j, i in enumerate(idxs):
        R = ref_of(name, i)
        print(f"{tag}[{i}] |ref|max={np.abs(R).max():6.2f}  rms={R.std():5.2f}")
        for k in (1, 8, 16):
            q = np.clip(np.round(R * k), -128, 127).astype(np.int8)
            p = os.path.join(OUT, f"{tag}{j}_k{k}.npy")
            np.save(p, q)
print("\nwritten to", OUT)
for f in sorted(os.listdir(OUT)):
    a = np.load(os.path.join(OUT, f))
    print(f"  {f:22s} shape={a.shape} dtype={a.dtype} min={a.min():4d} max={a.max():4d}")
