# -*- coding: utf-8 -*-
"""
下载 SynTTS-Commands 的 Free_ST_Chinese 子集（25 个中文命令，约 2.19GB）

来源：HuggingFace `lugan/Syntts-Commands-Media-Dataset`（论文 arXiv 2511.07821）
镜像：hf-mirror.com（HF 直连不通）
"""
import os

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "SynTTS-Free-ST-Chinese")

print(f"下载目标: {LOCAL}")
snapshot_download(
    repo_id="lugan/Syntts-Commands-Media-Dataset",
    repo_type="dataset",
    allow_patterns=["Free_ST_Chinese/*.zip"],
    local_dir=LOCAL,
)
print("下载完成")

# 列出结果
zips = sorted(f for f in os.listdir(os.path.join(LOCAL, "Free_ST_Chinese")) if f.endswith(".zip"))
print(f"共 {len(zips)} 个命令 zip:")
for z in zips:
    p = os.path.join(LOCAL, "Free_ST_Chinese", z)
    print(f"  {z:30s} {os.path.getsize(p)/1024/1024:.1f} MB")
