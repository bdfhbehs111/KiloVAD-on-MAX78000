import torch, os
LOG = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\ai8x-training\logs\one_base_withqat___2026.11.04-104409"
G   = r"C:\Users\13157\Desktop\work\blasphemy-edgeai\project-sys_agent\max78000\model_workspace\sentinal_model_train\one_base_withqat\_gin"
src = os.path.join(LOG, "one_base_qat_best-q.pth.tar")
ck  = torch.load(src, map_location="cpu", weights_only=False)
sd  = ck["state_dict"]
mods = ["conv1","conv2","conv3","conv4","conv5","conv6","fc"]
print("patched (output_shift -= activation_threshold):")
for m in mods:
    o, t = sd[f"{m}.output_shift"], sd[f"{m}.activation_threshold"]
    print(f"  {m:6s} {o.item():5.1f} - ({t.item():5.1f}) = {o.item()-t.item():5.1f}")
    sd[f"{m}.output_shift"] = torch.tensor([o.item() - t.item()])
out = os.path.join(G, "qat_shiftfix.pth.tar")
torch.save(ck, out)
print("->", out)
