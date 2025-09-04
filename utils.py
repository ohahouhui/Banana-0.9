from __future__ import annotations
import os, zipfile, shutil, time
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import nibabel as nib

def ensure_dir(p: Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def extract_zip(zip_path: Path, out_dir: Path) -> Path:
    out_dir = ensure_dir(out_dir)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(out_dir)
    return out_dir

def save_nifti_like(volume_np: np.ndarray, ref_affine: Optional[np.ndarray], out_path: Path):
    """
    volume_np: [Z, H, W] or [H, W, Z] 都可以，这里统一写入为 [H, W, Z]
    """
    arr = volume_np
    if arr.ndim != 3:
        raise ValueError("save_nifti_like expects 3D array.")
    # 统一到 [H, W, Z]
    # 约定：本工程内部体数据一律用 [Z, H, W]
    if arr.shape[0] < 8 and arr.shape[-1] > 64:
        # 看起来像 [H,W,Z]，不改
        hwz = arr
    else:
        # 认为是 [Z,H,W]
        hwz = np.transpose(arr, (1,2,0))
    affine = ref_affine if ref_affine is not None else np.eye(4, dtype=float)
    img = nib.Nifti1Image(hwz.astype(np.float32), affine)
    nib.save(img, str(out_path))

def percentile_thresh(x: np.ndarray, q: float) -> float:
    return float(np.percentile(x.reshape(-1), q))

def simple_box_smooth_1d(x: np.ndarray, k: int) -> np.ndarray:
    """一维盒滤（用于 z 方向平滑），k=1 表示不变"""
    if k <= 1: 
        return x
    k = int(k)
    pad = k // 2
    xpad = np.pad(x, (pad, pad), mode='edge')
    csum = np.cumsum(xpad, dtype=np.float64)
    out = (csum[k:] - csum[:-k]) / float(k)
    return out.astype(x.dtype)

def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())
