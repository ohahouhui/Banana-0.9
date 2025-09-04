from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def overlay_slice_png(vol_zhw: np.ndarray, mask_zhw: np.ndarray, z: int, out_png: Path, alpha: float=0.35):
    z = int(np.clip(z, 0, vol_zhw.shape[0]-1))
    img = vol_zhw[z]
    # 线性拉伸到 [0,1]（可视化）
    lo, hi = np.percentile(img, 1), np.percentile(img, 99)
    vv = np.clip((img - lo) / (hi - lo + 1e-6), 0, 1)

    plt.figure(figsize=(6,6))
    plt.imshow(vv, cmap="gray")
    m = mask_zhw[z].astype(bool)
    if m.any():
        # 画成红色半透明点云
        yy, xx = np.where(m)
        plt.scatter(xx, yy, s=1, alpha=alpha)
    plt.title(f"Overlay @ slice z={z}  img={vol_zhw.shape}  pred={mask_zhw.shape}")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    plt.close()
