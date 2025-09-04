from __future__ import annotations
from pathlib import Path
from typing import Tuple, Optional, List
import numpy as np
import pydicom
import nibabel as nib

def _load_dicom_series(folder: Path) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    dcm_files: List[Path] = sorted([p for p in folder.rglob("*.dcm") if p.is_file()])
    if not dcm_files:
        # 有些厂商无后缀，尝试所有文件中过滤 DICOM
        candidates = [p for p in folder.rglob("*") if p.is_file()]
        for p in candidates:
            try:
                ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
                if hasattr(ds, "SOPClassUID"):
                    dcm_files.append(p)
            except Exception:
                pass
        dcm_files.sort()
    if not dcm_files:
        raise FileNotFoundError(f"在 {folder} 未找到 .dcm 序列")

    # 读 meta 用于排序
    metas = []
    for p in dcm_files:
        ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        inst = getattr(ds, "InstanceNumber", None)
        ipp  = getattr(ds, "ImagePositionPatient", None)
        metas.append((p, inst, ipp))
    # 排序：优先 InstanceNumber，其次 ImagePositionPatient[2]
    def _zkey(t):
        p, inst, ipp = t
        if inst is not None:
            return int(inst)
        if ipp is not None and len(ipp) >= 3:
            return float(ipp[2])
        return 0
    metas.sort(key=_zkey)

    # 读像素并堆叠
    slices = []
    slope, inter = None, None
    for p, _, _ in metas:
        ds = pydicom.dcmread(str(p), force=True)
        arr = ds.pixel_array.astype(np.int16)
        # Hounsfield 估算
        slope = float(getattr(ds, "RescaleSlope", 1.0))
        inter = float(getattr(ds, "RescaleIntercept", 0.0))
        hu = arr * slope + inter
        slices.append(hu)
    vol = np.stack(slices, axis=0)  # [Z, H, W]

    # affine 简单设置（非严格，演示用）
    affine = np.eye(4, dtype=float)
    return vol.astype(np.float32), affine

def _load_nii(nii_path: Path) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    img = nib.load(str(nii_path))
    data = img.get_fdata().astype(np.float32)
    arr = np.asarray(data)
    # nib 为 [H,W,Z]，统一转 [Z,H,W]
    vol = np.transpose(arr, (2,0,1))
    return vol, img.affine

def load_any(input_path: Path) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    支持：
      - DICOM 文件夹
      - 打包的 ZIP（内含 DICOM 序列）
      - NIfTI (.nii / .nii.gz)
    返回：volume [Z,H,W]，affine（NIfTI 时可用）
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} 不存在")

    if input_path.suffix.lower() in [".nii", ".gz", ".nii.gz"]:
        return _load_nii(input_path)

    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        from utils import extract_zip
        tmp = input_path.parent / f"__unzipped_{input_path.stem}"
        if tmp.exists():
            # 清理旧目录
            import shutil; shutil.rmtree(tmp, ignore_errors=True)
        extract_zip(input_path, tmp)
        return _load_dicom_series(tmp)

    if input_path.is_dir():
        return _load_dicom_series(input_path)

    raise ValueError(f"无法识别的输入：{input_path}")
