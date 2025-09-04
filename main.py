# -*- coding: utf-8 -*-
r"""
Banana — 单次推理入口（双报告版）
- 保持原有专业报告与文件产物不变
- 额外生成大众版结论（*_report_easy.txt）

用法（与之前一致）：
  python main.py --input "<你的zip或nii路径>" --out "outputs"

注意：Windows 路径请用引号包住，或使用反斜杠转义已由 argparse 处理。
"""

import os, sys, json, math, time, argparse
from pathlib import Path

import numpy as np
import nibabel as nib
import SimpleITK as sitk

# ------------ 可选依赖（没有也能跑，只是会少做连通域清理） ------------
try:
    from scipy import ndimage as ndi
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

# ------------ 参数默认（与你之前保持一致） ------------
DEF_HU_WIN   = (-200.0, 400.0)    # 可视化窗
DEF_SOFT_HU  = (-250.0, 200.0)    # 参与筛选的软阈 HU
DEF_TOP_PCT  = 0.60               # 取top百分位作为初阈值
DEF_Z_SMOOTH = 1                  # z 方向平滑（示意位）
DEF_MIN_AREA = 80                 # 连通域最小体素

# ------------ 日志辅助 ------------
def log(msg: str):
    now = time.strftime("%Y/%m/%d %H:%M:%S")
    print(f"[{now}] {msg}")

# ------------ I/O：读取 zip/DICOM/nii(.gz) ------------
def load_any(input_path: Path):
    """
    返回：
      vol: np.float32, 形状 [Z,H,W]（CT 的 HU 值）
      affine: 4x4 仿射（没有就造一个1mm各向同性）
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"{p} 不存在")

    # 1) 直接 NIfTI
    if p.suffix.lower() in [".nii", ".gz", ".mgz", ".mgh"] or p.name.endswith(".nii.gz"):
        img = nib.load(str(p))
        vol = np.asarray(img.get_fdata()).astype(np.float32)
        affine = img.affine.astype(np.float32)
        # 兼容 [H,W,Z] or [Z,H,W]：统一成 [Z,H,W]
        if vol.shape[0] != min(vol.shape):
            # 约定 NIfTI 常为 [H,W,Z]，这里转为 [Z,H,W]
            vol = np.moveaxis(vol, -1, 0)
        return vol, affine

    # 2) DICOM 文件夹（或zip解压出的文件夹）
    if p.is_dir():
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(str(p))
        if not dicom_names:
            raise FileNotFoundError("未在目录中找到 DICOM 序列")
        reader.SetFileNames(dicom_names)
        img = reader.Execute()
        vol = sitk.GetArrayFromImage(img).astype(np.float32)  # [Z,H,W]
        # 构造affine（近似）：spacing 放对，方向不强依赖
        sp = img.GetSpacing()           # (sx, sy, sz)
        origin = img.GetOrigin()        # (ox, oy, oz)
        affine = np.eye(4, dtype=np.float32)
        # 注意 SimpleITK 的 spacing  顺序与数组轴不完全一致；这里用体素体积不受方向影响
        affine[0,0] = sp[2]  # z
        affine[1,1] = sp[1]  # y
        affine[2,2] = sp[0]  # x
        affine[:3,3] = np.array(origin[::-1], dtype=np.float32)
        return vol, affine

    # 3) zip：解压到临时目录后走 DICOM 文件夹逻辑
    if p.suffix.lower() == ".zip":
        import zipfile, tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="banana_"))
        with zipfile.ZipFile(str(p), "r") as zf:
            zf.extractall(tmpdir)
        # 尝试寻找包含 .dcm 的最内层目录
        cand = None
        for root, _, files in os.walk(tmpdir):
            if any(f.lower().endswith(".dcm") for f in files):
                cand = Path(root); break
        if cand is None:
            raise FileNotFoundError("zip 内未发现 DICOM 文件（*.dcm）")
        return load_any(cand)

    raise ValueError(f"不支持的输入：{p}")

# ------------ 体素体积（mm^3） ------------
def voxel_volume_mm3(affine: np.ndarray | None) -> float:
    if affine is None:
        return 1.0
    try:
        return float(abs(np.linalg.det(affine[:3, :3])))
    except Exception:
        return 1.0

# ------------ 归一化用于显示 ------------
def normalize_to_01(vol: np.ndarray, win: tuple[float, float]):
    lo, hi = win
    v = np.clip(vol, lo, hi)
    v = (v - lo) / (hi - lo + 1e-6)
    return v

# ------------ “银标准”筛选（非常轻量，不依赖深度模型） ------------
def silver_mask(vol_hu: np.ndarray,
                soft_hu: tuple[float, float],
                top_percent: float,
                z_smooth_k: int,
                min_area: int):
    """
    返回二值 mask（uint8，0/1），形状与 vol_hu 一致
    """
    lo, hi = soft_hu
    v = np.clip(vol_hu, lo, hi)
    # 百分位阈值
    thr = np.quantile(v[v > lo], 1.0 - top_percent)
    init = (v >= thr).astype(np.uint8)

    # z 向“平滑”示意：简单多数投票
    if z_smooth_k > 1:
        k = max(1, int(z_smooth_k))
        pad = k // 2
        padded = np.pad(init, ((pad, pad), (0, 0), (0, 0)), constant_values=0)
        acc = np.zeros_like(init, dtype=np.int32)
        for dz in range(k):
            acc += padded[dz:dz+init.shape[0], :, :]
        init = (acc >= (k+1)//2).astype(np.uint8)

    # 连通域清理（可选）
    if _HAS_SCIPY and min_area > 0:
        lab, nlab = ndi.label(init > 0)
        sizes = np.bincount(lab.ravel())
        remove_ids = np.where(sizes < min_area)[0]
        # 0 是背景，跳过
        for rid in remove_ids:
            if rid == 0: continue
            init[lab == rid] = 0

    return init, float(thr)

# ------------ 叠图（取中间层） ------------
def save_overlay_mid(vol01: np.ndarray, mask01: np.ndarray, out_png: Path):
    z = vol01.shape[0] // 2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(6,6))
    plt.imshow(vol01[z], cmap="gray")
    plt.imshow(mask01[z], cmap="Reds", alpha=0.35)
    plt.title(f"Overlay @ z={z}  img={tuple(vol01.shape)}  pred={tuple(mask01.shape)}")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_png, dpi=120)
    plt.close()

# ------------ 风险评级 & 大小类比 & 建议 ------------
def risk_str(volume_ml: float, clean_voxels: int) -> tuple[str, float]:
    """
    非医学诊断，仅供演示。给出一个“疑似风险百分比”和等级文案。
    """
    if clean_voxels <= 0 or volume_ml <= 1:
        return ("极低", 2.0)

    # 阈值可按你后续数据再调
    if volume_ml >= 1000:
        return ("高", 85.0)
    if volume_ml >= 200:
        return ("中", 55.0)
    return ("低", 20.0)

def size_analogy(volume_ml: float) -> tuple[str, float, float]:
    """
    把体积换算为等体积球体的直径，给出一个生活化类比。
    返回：(类比, 直径cm, 半径cm)
    """
    # V = 4/3 π r^3（cm^3 = ml）
    if volume_ml <= 0:
        return ("小于米粒", 0.2, 0.1)
    r_cm = ((volume_ml * 3.0) / (4.0 * math.pi)) ** (1.0/3.0)
    d_cm = 2.0 * r_cm
    # 粗略映射
    if d_cm < 1.0:      tag = "米粒大小"
    elif d_cm < 2.0:    tag = "黄豆大小"
    elif d_cm < 3.5:    tag = "花生/葡萄大小"
    elif d_cm < 4.5:    tag = "乒乓球/小核桃大小"
    elif d_cm < 6.0:    tag = "鸡蛋大小"
    elif d_cm < 8.0:    tag = "橙子大小"
    else:               tag = "网球及以上"
    return (tag, round(d_cm, 1), round(r_cm, 1))

def easy_recommendation(risk_level: str) -> str:
    if risk_level == "高":
        return "建议尽快完善增强CT或MRI，并至肝胆外科/肿瘤专科门诊就诊；必要时MDT评估与病理活检。"
    if risk_level == "中":
        return "建议预约门诊复查，完善增强CT或MRI随访；结合肿瘤标志物、病史综合判断。"
    return "建议常规随访或结合症状与既往史评估；如有不适请及时就诊。"

# ------------ 主流程 ------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="DICOM打包zip / DICOM文件夹 / .nii/.nii.gz")
    ap.add_argument("--out",   required=True, help="输出目录")
    ap.add_argument("--hu_lo",    type=float, default=DEF_HU_WIN[0])
    ap.add_argument("--hu_hi",    type=float, default=DEF_HU_WIN[1])
    ap.add_argument("--soft_lo",  type=float, default=DEF_SOFT_HU[0])
    ap.add_argument("--soft_hi",  type=float, default=DEF_SOFT_HU[1])
    ap.add_argument("--top_percent", type=float, default=DEF_TOP_PCT)
    ap.add_argument("--z_smooth",   type=int,   default=DEF_Z_SMOOTH)
    ap.add_argument("--min_area",   type=int,   default=DEF_MIN_AREA)
    args = ap.parse_args()

    inp   = Path(args.input)
    outd  = Path(args.out); outd.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    case  = inp.stem.replace(" ", "_")
    prefix = f"{case}_{stamp}"

    # 1) 读取体积
    log(f"[1] 读取：{inp}")
    vol_hu, affine = load_any(inp)            # [Z,H,W] float32
    Z,H,W = vol_hu.shape
    vox_mm3 = voxel_volume_mm3(affine)
    log(f"体素体积(mm^3) ≈ {vox_mm3:.6f}  体积形状：[Z,H,W]={vol_hu.shape}")

    # 2) “银标准”掩膜
    log(f"[2] 筛选（soft={args.soft_lo}~{args.soft_hi} HU, top={args.top_percent*100:.0f}%）")
    mask, thr = silver_mask(
        vol_hu,
        soft_hu=(args.soft_lo, args.soft_hi),
        top_percent=float(args.top_percent),
        z_smooth_k=int(args.z_smooth),
        min_area=int(args.min_area),
    )  # uint8

    voxels_raw  = int(mask.sum())
    vol01       = normalize_to_01(vol_hu, (args.hu_lo, args.hu_hi))
    mask01      = (mask > 0).astype(np.uint8)

    # 3) 保存 NIfTI（影像 & 掩膜）
    log("[3] 保存 NIfTI")
    img_nii  = nib.Nifti1Image(vol_hu, affine if affine is not None else np.eye(4, dtype=np.float32))
    mask_nii = nib.Nifti1Image(mask01.astype(np.uint8), img_nii.affine)
    img_path  = outd / f"{prefix}_image.nii.gz"
    mask_path = outd / f"{prefix}_image_mask.nii.gz"
    nib.save(img_nii,  str(img_path))
    nib.save(mask_nii, str(mask_path))

    # 4) 保存叠图（中间层）
    ov_png = outd / f"{prefix}_overlay_z50.png"
    save_overlay_mid(vol01, mask01, ov_png)

    # 5) 统计与体积
    volume_mm3 = vox_mm3 * float(mask01.sum())
    volume_ml  = volume_mm3 / 1000.0

    # 6) 专业版报告（沿用你原先口径，单位与字段更清楚）
    pro_txt = outd / f"{prefix}_report_pro.txt"
    with open(pro_txt, "w", encoding="utf-8") as f:
        f.write(
            "【Banana 专业报告】\n"
            f"输入：{str(inp)}\n"
            f"输出目录：{str(outd)}\n"
            f"体素体积(mm^3/voxel)：{vox_mm3:.6f}\n"
            f"体积维度 [Z,H,W]：{list(vol_hu.shape)}\n"
            f"软阈区间（用于掩膜）：[{args.soft_lo:.1f}, {args.soft_hi:.1f}] HU\n"
            f"Top百分比：{args.top_percent:.2f}\n"
            f"连通域下限：{args.min_area} 体素\n"
            f"阈值（自动计算）：{thr:.3f} HU（在软阈范围内的分位）\n"
            f"掩膜体素（raw）：{voxels_raw}\n"
            f"病灶体积(mm^3)：{volume_mm3:.3f}\n"
            f"病灶体积(ml)：{volume_ml:.3f}\n"
            f"影像：{img_path.name}\n"
            f"掩膜：{mask_path.name}\n"
            f"叠图：{ov_png.name}\n"
        )

    # 7) 大众版结论
    level, risk_pct = risk_str(volume_ml, voxels_raw)
    tag, d_cm, r_cm = size_analogy(volume_ml)
    easy_txt = outd / f"{prefix}_report_easy.txt"
    with open(easy_txt, "w", encoding="utf-8") as f:
        f.write(
            "【Banana 大众版结论（演示用，非最终医疗诊断）】\n"
            f"疑似风险：{level}（约 {risk_pct:.0f}%）\n"
            f"疑似区域总体积：约 {volume_ml:.1f} ml\n"
            f"等体积球体直径：约 {d_cm:.1f} cm（{tag}）\n"
            f"下一步建议：{easy_recommendation(level)}\n"
            "\n"
            "温馨提示：本工具为科研原型，结论仅供参考，请结合增强影像、临床表现与专科医生意见。\n"
        )

    # 8) JSON（便于前端或二次开发）
    rep_json = {
        "input": str(inp),
        "output_dir": str(outd),
        "shape": [int(Z), int(H), int(W)],
        "voxel_volume_mm3": float(vox_mm3),
        "soft_mask_hu": [float(args.soft_lo), float(args.soft_hi)],
        "top_percent": float(args.top_percent),
        "min_area": int(args.min_area),
        "threshold_in_soft": float(thr),
        "voxels_raw": int(voxels_raw),
        "volume_mm3": float(volume_mm3),
        "volume_ml": float(volume_ml),
        "risk_level": level,
        "risk_pct": float(risk_pct),
        "size_tag": tag,
        "equiv_diameter_cm": float(d_cm),
        "equiv_radius_cm": float(r_cm),
        "image": img_path.name,
        "mask": mask_path.name,
        "overlay": ov_png.name,
        "created_at": stamp,
    }
    with open(outd / f"{prefix}_report.json", "w", encoding="utf-8") as f:
        json.dump(rep_json, f, ensure_ascii=False, indent=2)

    log(f"✅ 完成：{prefix}")
    log(f" - 专业版：{pro_txt.name}")
    log(f" - 大众版：{easy_txt.name}")
    log(f" - JSON：   {prefix}_report.json")
    log("（声明：以上为原型演示结果，非医学诊断）")

if __name__ == "__main__":
    main()
