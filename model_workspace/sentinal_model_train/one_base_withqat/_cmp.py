import torch, os
G = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
OLD = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\ai8x-training\logs\one_base_withqat___2026.11.04-104409\one_base_qat_best-q.pth.tar"
mods = ["conv1","conv2","conv3","conv4","conv5","conv6","fc"]
new = torch.load(os.path.join(G,"qat_recal.pth.tar"), map_location="cpu", weights_only=False)["state_dict"]
old = torch.load(OLD, map_location="cpu", weights_only=False)["state_dict"]
print(f"{'layer':7s} {'OLD out_shift':>13s} {'NEW out_shift':>13s} {'thr':>6s} {'final_scale':>11s}")
for m in mods:
    print(f"{m:7s} {old[m+'.output_shift'].item():13.1f} {new[m+'.output_shift'].item():13.1f} "
          f"{new[m+'.activation_threshold'].item():6.1f} {new[m+'.final_scale'].item():11.1f}")
print()
print("weight range / bias range (new):")
for m in mods:
    w = new[m+".op.weight"]; b = new[m+".op.bias"]
    print(f"  {m:7s} w=[{w.min():6.0f},{w.max():6.0f}]  b=[{b.min():9.0f},{b.max():9.0f}]")
