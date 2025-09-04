# -*- coding: utf-8 -*-
"""
生成“文字说明 + 图像”同一份 PDF（单文件）。
会在 outputs/ 中寻找最新一次结果：
- 文本：*_report_easy.txt 优先；否则 *_report.txt / *_report.json
- 图片：*_overlay_z*.png 优先；否则 *_image.nii.gz 的占位图（如果没有 PNG）
输出：*_report.pdf 写回到 outputs/
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path
from datetime import datetime

from fpdf import FPDF
from PIL import Image

def find_latest_group(out_dir: Path) -> dict:
    """
    在 out_dir 找一组同名前缀的产物，按时间最新的那组。
    返回 dict: {prefix, easy_txt, full_txt, json, overlay_pngs, png_any}
    """
    out_dir = Path(out_dir)
    items = sorted(out_dir.glob("*_report.txt")) + sorted(out_dir.glob("*_report.json")) + sorted(out_dir.glob("*_overlay_z*.png"))
    if not items:
        raise FileNotFoundError(f"在 {out_dir} 未找到任何可用输出。")

    # 取最后修改时间最新的“前缀”
    # 例如：case_20250821_095616_xxx => 前缀是 case_20250821_095616
    def prefix_of(p: Path) -> str:
        m = re.match(r"(.+?)_(image|image_mask|overlay_z\d+|report|report\.json)", p.stem)
        return m.group(1) if m else p.stem

    # 找到最新文件的前缀
    newest = max(items, key=lambda p: p.stat().st_mtime)
    prefix = prefix_of(newest)

    group = {
        "prefix": prefix,
        "easy_txt": next(iter(sorted(out_dir.glob(f"{prefix}_report_easy.txt"))), None),
        "full_txt": next(iter(sorted(out_dir.glob(f"{prefix}_report.txt"))), None),
        "json":     next(iter(sorted(out_dir.glob(f"{prefix}_report.json"))), None),
        "overlay_pngs": sorted(out_dir.glob(f"{prefix}_overlay_z*.png")),
        "png_any":  sorted(out_dir.glob("*.png")),
    }
    return group

def read_summary(group: dict) -> str:
    """
    读取大众版或专业版文本；若两者都没有，再从 json 提炼关键信息。
    返回纯文本（会被打印在 PDF 里）
    """
    if group["easy_txt"] and group["easy_txt"].exists():
        return group["easy_txt"].read_text(encoding="utf-8", errors="ignore")

    if group["full_txt"] and group["full_txt"].exists():
        return group["full_txt"].read_text(encoding="utf-8", errors="ignore")

    if group["json"] and group["json"].exists():
        data = json.loads(group["json"].read_text(encoding="utf-8", errors="ignore"))
        # 简单拼一个摘要
        lines = []
        lines.append("【Banana 自动分析摘要】")
        if "input" in data:       lines.append(f"输入：{data['input']}")
        if "output_dir" in data:  lines.append(f"输出目录：{data['output_dir']}")
        if "stats" in data and isinstance(data["stats"], dict):
            st = data["stats"]
            shp = st.get("shape", None)
            if shp: lines.append(f"体素维度[Z,H,W]：{shp}")
            if "threshold" in st: lines.append(f"自动阈值（HU）：{round(st['threshold'],3)}")
            if "voxels_raw" in st: lines.append(f"原始体素数：{st['voxels_raw']}")
            if "voxels_clean" in st: lines.append(f"清理后体素数：{st['voxels_clean']}")
            if "vol_mm3" in st: lines.append(f"病灶体积(mm^3)：{round(st['vol_mm3'],3)}")
            if "vol_ml" in st:  lines.append(f"病灶体积(ml)：{round(st['vol_ml'],3)}")
        if "advice" in data:      lines.append(f"建议：{data['advice']}")
        return "\n".join(lines)

    return "（未找到文本报告，仅生成图像页）"

def choose_image(group: dict) -> Path | None:
    """
    选择一张要放进 PDF 的图片：优先 overlay，找不到就随便挑一张 png。
    """
    if group["overlay_pngs"]:
        return group["overlay_pngs"][0]
    if group["png_any"]:
        return group["png_any"][0]
    return None

def add_footer(pdf: FPDF, text: str):
    pdf.set_y(-15)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(150,150,150)
    pdf.cell(0, 10, text, 0, 0, "R")

def mm(v: float) -> float:
    return float(v)

def build_pdf(out_dir: Path) -> Path:
    group = find_latest_group(out_dir)
    summary = read_summary(group)
    img_path = choose_image(group)

    # 输出文件名
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = Path(out_dir) / f"{group['prefix']}_report.pdf"

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False, margin=mm(15))

    # ============ 第 1 页：文字 + 大图在同一页 ============
    pdf.add_page()

    # 标题
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0,0,0)
    pdf.cell(0, 12, "Banana 自動分析報告 (演示用)", 0, 1, "L")

    # 左侧文字框
    left_x, top_y, right_x = mm(15), mm(25), mm(195)
    text_w = mm(90)  # 左边放文字 90mm
    img_x = left_x + text_w + mm(5)  # 右边图片与文字间隔 5mm
    img_w = right_x - img_x  # 右侧能用的宽度

    # 文字
    pdf.set_font("Helvetica", size=11)
    pdf.set_xy(left_x, top_y)
    # 将多行文本分段输出，避免一次性 cell 太长
    for para in summary.splitlines():
        if not para.strip():
            pdf.ln(4)
            continue
        pdf.multi_cell(text_w, 6, para, 0, "L")

    # 右侧放图（等比例缩放）
    if img_path and img_path.exists():
        try:
            with Image.open(img_path) as im:
                w, h = im.size
            # 计算等比缩放，图高不超过 150mm
            max_h = mm(150)
            # 根据目标宽度 img_w 先算缩放后的高度
            scale_h = h * (img_w / w)
            if scale_h > max_h:
                # 超高则以高度限制，再反算宽度
                disp_h = max_h
                disp_w = w * (disp_h / h)
            else:
                disp_w = img_w
                disp_h = scale_h
            # 垂直位置：与文字顶部对齐
            pdf.image(str(img_path), x=img_x, y=top_y, w=disp_w, h=disp_h)
        except Exception as e:
            pdf.set_xy(img_x, top_y)
            pdf.set_text_color(180,0,0)
            pdf.multi_cell(img_w, 6, f"加载图片失败：{img_path.name}\n{e}", 0, "L")
    else:
        pdf.set_xy(img_x, top_y)
        pdf.set_text_color(120,120,120)
        pdf.multi_cell(img_w, 6, "未找到可用的 PNG 图像。", 0, "L")

    # 页脚
    add_footer(pdf, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  {group['prefix']}")

    # 保存
    pdf.output(str(pdf_path))
    return pdf_path

def main():
    # 命令：python make_pdf.py --in_dir C:\...\outputs
    # 默认为脚本同目录的 outputs
    in_dir = None
    args = sys.argv[1:]
    if "--in_dir" in args:
        i = args.index("--in_dir")
        if i+1 < len(args):
            in_dir = Path(args[i+1])
    if not in_dir:
        in_dir = Path(__file__).resolve().parent / "outputs"

    pdfp = build_pdf(in_dir)
    print(f"[+] PDF 已生成：{pdfp}")

if __name__ == "__main__":
    main()
