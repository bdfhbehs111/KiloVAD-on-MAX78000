import numpy as np, os
G = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
for f in sorted(os.listdir(G)):
    if not f.endswith(".npy"): continue
    a = np.load(os.path.join(G, f))
    np.save(os.path.join(G, f), a.astype(np.int64))
    print(f"{f} -> int64  min={a.min():4d} max={a.max():4d}")
