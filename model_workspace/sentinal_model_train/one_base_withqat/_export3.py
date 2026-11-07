import numpy as np, os
DATA = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_dataset\dataset_processed"
G = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
rng = np.random.default_rng(11)
for name, tag in (("pos","voice"),("neg","noise")):
    m = np.load(os.path.join(DATA, f"{name}_X.npy"), mmap_mode="r")
    sp = np.load(os.path.join(DATA, f"{name}_split.npy"))
    idx = np.sort(rng.choice(np.flatnonzero(sp==2), size=4, replace=False))
    for j,i in enumerate(idx):
        x = np.asarray(m[i], dtype=np.float32)
        R = (x-x.mean(-1,keepdims=True))/(x.std(-1,ddof=1,keepdims=True)+1e-5)
        for k in (32,64,128):
            np.save(os.path.join(G, f"{tag}{j}_k{k}.npy"),
                    np.clip(np.round(R*k),-128,127).astype(np.int64))
print("ok")
