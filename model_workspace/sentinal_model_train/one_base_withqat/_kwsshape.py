import numpy as np, os
p = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000_backup\ai8x-synthesis\tests\sample_kws_20.npy"
a = np.load(p)
print("kws sample:", a.shape, a.dtype, "min", a.min(), "max", a.max())
