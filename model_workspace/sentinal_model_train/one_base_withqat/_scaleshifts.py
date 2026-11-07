import torch, os
G = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
sd = torch.load(os.path.join(G,"q_SCALE.pth.tar"), map_location="cpu", weights_only=False)["state_dict"]
for m in ["conv1","conv2","conv3","conv4","conv5","conv6","fc"]:
    w = sd[m+".op.weight"]
    print(f"  {m:6s} shift={sd[m+'.output_shift'].item():5.1f}  w=[{w.min():6.0f},{w.max():6.0f}]  final_scale={sd[m+'.final_scale'].item():.0f}")
