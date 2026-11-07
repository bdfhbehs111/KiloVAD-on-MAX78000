import torch, os, glob
G = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
mods = ["conv1","conv2","conv3","conv4","conv5","conv6","fc"]
for f in sorted(glob.glob(os.path.join(G, "q_*.pth.tar"))) + [os.path.join(G,"qat_recal.pth.tar")]:
    sd = torch.load(f, map_location="cpu", weights_only=False)["state_dict"]
    print(os.path.basename(f))
    for m in mods:
        w = sd[m+".op.weight"]
        print(f"   {m:6s} shift={sd[m+'.output_shift'].item():5.1f} w=[{w.min():6.0f},{w.max():6.0f}]")
