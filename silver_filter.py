from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np
from utils import percentile_thresh, simple_box_smooth_1d

def window_and_norm(vol_zhw: np.ndarray, lo: float=-200.0, hi: float=400.0) -> np.ndarray:
    """HU 窗口截断并归一化到 [0,1]，vol 为 [Z,H,W]"""
    v = np.clip(vol_zhw, lo, hi)
    v = (v - lo) / (hi - lo + 1e-6)
    return v.astype(np.float32)

def remove_small_objects_slice(mask2d: np.ndarray, min_area: int=80) -> np.ndarray:
    """
    纯 NumPy 的 2D 连通域去小块（4 连通）。为避免 SciPy 依赖。
    """
    H, W = mask2d.shape
    lab = -np.ones_like(mask2d, dtype=np.int32)
    cur = 0
    areas = []
    # 邻接（上、下、左、右）
    for y in range(H):
        for x in range(W):
            if mask2d[y,x] == 0 or lab[y,x] != -1:
                continue
            # flood fill
            stack = [(y,x)]
            lab[y,x] = cur
            cnt = 0
            while stack:
                yy, xx = stack.pop()
                cnt += 1
                if yy>0 and mask2d[yy-1,xx] and lab[yy-1,xx]==-1:
                    lab[yy-1,xx]=cur; stack.append((yy-1,xx))
                if yy<H-1 and mask2d[yy+1,xx] and lab[yy+1,xx]==-1:
                    lab[yy+1,xx]=cur; stack.append((yy+1,xx))
                if xx>0 and mask2d[yy,xx-1] and lab[yy,xx-1]==-1:
                    lab[yy,xx-1]=cur; stack.append((yy,xx-1))
                if xx<W-1 and mask2d[yy,xx+1] and lab[yy,xx+1]==-1:
                    lab[yy,xx+1]=cur; stack.append((yy,xx+1))
            areas.append(cnt); cur += 1
    if cur == 0:
        return mask2d
    areas = np.array(areas, dtype=np.int32)
    keep = areas >= int(min_area)
    out = (keep[lab] if keep.size>0 else np.zeros_like(mask2d)).astype(np.uint8)
    return out

def clean_small_objects_3d(mask_zhw: np.ndarray, min_area: int=80) -> np.ndarray:
    """逐切片去小块，然后沿 z 方向做多数投票平滑。"""
    Z,H,W = mask_zhw.shape
    cleaned = np.zeros_like(mask_zhw, dtype=np.uint8)
    for z in range(Z):
        cleaned[z] = remove_small_objects_slice(mask_zhw[z].astype(np.uint8), min_area=min_area)
    # z 方向 3 切片多数票
    if Z >= 3:
        m = cleaned.astype(np.int16)
        m_shift1 = np.pad(m[1:], ((0,1),(0,0),(0,0)), mode="edge")
        m_shift2 = np.pad(m[:-1], ((1,0),(0,0),(0,0)), mode="edge")
        votes = m + m_shift1 + m_shift2
        cleaned = (votes >= 2).astype(np.uint8)
    return cleaned

def silver_infer(vol_zhw: np.ndarray, *,
                 hu_window: Tuple[float,float]=(-200,400),
                 soft_mask_hu: Tuple[float,float]=(-250,200),
                 top_percent: float=0.6,
                 z_smooth_k: int=1,
                 min_area: int=80) -> Dict[str,Any]:
    """
    极简“银标准”：
      1) HU 窗口标准化
      2) 生成软组织 mask（排除空气/高骨）
      3) 取软组织体素中强度 Top P% 作为可疑区
      4) 逐切片去小连通域 + z 向多数投票
    返回：pred_mask、概率/强度图（用于可视化）、若干统计量
    """
    Z,H,W = vol_zhw.shape
    v01 = window_and_norm(vol_zhw, lo=hu_window[0], hi=hu_window[1])  # [0,1]

    # 软组织范围（基于 HU 原值）
    soft = (vol_zhw >= soft_mask_hu[0]) & (vol_zhw <= soft_mask_hu[1])

    # 可选择 z 方向平滑（按体素强度对每个 (y,x) 做 1D 盒滤）
    if z_smooth_k > 1:
        v_sm = np.empty_like(v01)
        for y in range(H):
            v_sm[:,y,:] = np.apply_along_axis(simple_box_smooth_1d, 0, v01[:,y,:], z_smooth_k)
        v01 = v_sm

    # 阈值 = 软组织内百分位
    cand_vals = v01[soft]
    if cand_vals.size == 0:
        th = 0.98  # 极端兜底
    else:
        th = percentile_thresh(cand_vals, 100.0 - float(top_percent))  # 例如 top_percent=0.6 → 99.4 分位
        th = max(min(th, 0.995), 0.50)  # 合理夹紧

    raw_mask = ((v01 >= th) & soft).astype(np.uint8)
    clean_mask = clean_small_objects_3d(raw_mask, min_area=min_area)

    stats = {
        "shape": (Z,H,W),
        "threshold": float(th),
        "voxels_raw": int(raw_mask.sum()),
        "voxels_clean": int(clean_mask.sum()),
        "ratio_clean": float(clean_mask.sum() / (Z*H*W)),
    }
    return {
        "mask": clean_mask,
        "scoremap": v01,   # 用于叠加显示
        "stats": stats,
    }
