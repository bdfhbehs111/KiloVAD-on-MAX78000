import numpy as np, os
G = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
np.save(os.path.join(G,"EXT_zero.npy"), np.zeros((128,128), np.int64))
np.save(os.path.join(G,"EXT_pos127.npy"), np.full((128,128), 127, np.int64))
np.save(os.path.join(G,"EXT_neg128.npy"), np.full((128,128), -128, np.int64))
np.save(os.path.join(G,"EXT_alt.npy"), (np.arange(128)[None,:]%2*254-127).repeat(128,0).astype(np.int64))
print("ok")
