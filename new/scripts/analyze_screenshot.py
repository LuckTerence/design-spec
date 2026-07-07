#!/usr/bin/env python3
"""截图分析引擎 — colorthief + coloraide 版

从 screenshot 提取设计令牌，输出 DESIGN.md 格式的设计令牌，含置信度标注。

实现说明（尽量复用成熟轮子）：
  - 调色板提取：colorthief（MMCQ 量化，纯 Python，仅依赖 Pillow），
    取代自研的 KMeans + scikit-learn 方案，依赖更轻、质量更稳。
  - 颜色科学（亮度 / 对比度）：coloraide（WCAG 21 全量支持），
    取代手写 sRGB 线性化与相对亮度公式。
改进点：
  - 移除 numpy / scikit-learn 重依赖
  - 颜色语义推断（primary/background/text/surface）附带置信度
  - 3 位 hex 安全处理
"""

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, List, Tuple

from PIL import Image, ImageStat
from coloraide import Color as CColor
from colorthief import ColorThief


# ── 常量 ───────────────────────────────────────────────────────

FALLBACK_PRIMARY = "#1A73E8"
FALLBACK_SECONDARY = "#34A853"
FALLBACK_BACKGROUND = "#FFFFFF"
FALLBACK_TEXT_DARK = "#1A1C1E"
FALLBACK_TEXT_LIGHT = "#E8EAED"


# ── 颜色工具（委托 coloraide） ──────────────────────────────────

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) < 6:
        h = h.ljust(6, "0")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return CColor("rgb({}, {}, {})".format(int(r), int(g), int(b))).convert("srgb").to_string(
        hex=True, alpha=False
    )


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    return CColor("rgb({}, {}, {})".format(*rgb)).luminance()


def _is_dark(hex_color: str) -> bool:
    return _relative_luminance(_hex_to_rgb(hex_color)) < 0.179


def _contrast_ratio(c1: str, c2: str) -> float:
    try:
        return CColor(c1).contrast(CColor(c2), method="wcag21")
    except Exception:
        return 1.0


def _saturation(rgb: Tuple[int, int, int]) -> float:
    r, g, b = [c / 255.0 for c in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    return (mx - mn) / mx if mx > 0 else 0.0


def _is_neutral(rgb: Tuple[int, int, int], threshold: float = 0.08) -> bool:
    r, g, b = [c / 255.0 for c in rgb]
    avg = (r + g + b) / 3.0
    return max(abs(r - avg), abs(g - avg), abs(b - avg)) < threshold


def _color_distance(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


# ── 颜色聚类（委托 colorthief） ─────────────────────────────────

def _sample_pixels(img: Image.Image) -> List[Tuple[int, int, int]]:
    small = img.convert("RGB").copy()
    small.thumbnail((800, 800))
    w, h = small.size
    step = max(2, min(w, h) // 60)
    return [small.getpixel((x, y)) for y in range(0, h, step) for x in range(0, w, step)]


def _frequency_palette(img: Image.Image, n_colors: int) -> List[Tuple[int, int, int]]:
    small = img.convert("RGB").copy()
    small.thumbnail((100, 100))
    cnt = Counter(small.getdata())
    return [c for c, _ in cnt.most_common(max(2, n_colors))]


def extract_palette(image_path: str, n_colors: int = 10) -> List[Dict]:
    """用 colorthief（MMCQ）提取主色调，再按最近邻统计占比。"""
    try:
        img = Image.open(image_path).convert("RGB")
    except (IOError, OSError) as e:
        print(f"错误：无法打开图片 — {image_path}: {e}")
        sys.exit(1)

    try:
        pal = ColorThief(image_path).get_palette(color_count=max(2, n_colors), quality=10)
    except Exception as e:
        print(f"Warning: colorthief failed ({e}), using frequency fallback")
        pal = _frequency_palette(img, n_colors)

    if not pal:
        pal = _frequency_palette(img, n_colors)

    pal = list(dict.fromkeys(pal))  # 去重并保持顺序

    samples = _sample_pixels(img)
    if not samples:
        samples = [img.getpixel((0, 0))]
    counts = Counter(
        min(pal, key=lambda c: sum((px[i] - c[i]) ** 2 for i in range(3))) for px in samples
    )
    total = len(samples)

    result = []
    for c, cnt in counts.most_common():
        r, g, b = c
        result.append({
            "hex": _rgb_to_hex(r, g, b),
            "rgb": (int(r), int(g), int(b)),
            "pixels": cnt,
            "ratio": round(cnt / total, 3),
        })
    return result


# ── 主题检测 ────────────────────────────────────────────────────

def detect_theme(image_path: str) -> Dict[str, str]:
    """检测浅色/深色主题，使用中位数亮度提高鲁棒性。"""
    img = Image.open(image_path).convert("L")
    stat = ImageStat.Stat(img)
    median_luminance = stat.median[0]
    avg_luminance = stat.mean[0]
    combined = 0.6 * avg_luminance + 0.4 * median_luminance
    return {
        "theme": "dark" if combined < 128 else "light",
        "avg_luminance": round(avg_luminance, 1),
        "median_luminance": round(median_luminance, 1),
    }


# ── 颜色语义推断 ────────────────────────────────────────────────

def infer_semantic_colors(palette: List[Dict], theme: str) -> Dict[str, str]:
    """从主色调中推断语义颜色：primary/secondary/background/text/surface。

    启发式规则：
      - background: 占比最高且接近中性（白/灰/黑）的颜色
      - primary: 非中性、饱和度最高、占比适中的颜色；优先排除背景与文字候选
      - text: 与背景对比度最高的颜色，优先深色/浅色文字
      - surface: 第二常见的中性或近中性色，用于卡片/浮层
      - secondary: 与 primary/background/text 差异明显的另一非中性色
    """
    colors = {}

    neutrals = [c for c in palette if _is_neutral(c["rgb"])]
    if neutrals:
        bg = max(neutrals, key=lambda c: c["ratio"])
    else:
        bg = max(palette, key=lambda c: c["ratio"])
    colors["background"] = bg["hex"]

    bg_rgb = bg["rgb"]

    def near_bg(c):
        return _color_distance(c["rgb"], bg_rgb) < 25

    non_bg = [c for c in palette if not near_bg(c)]

    text_candidates = [c for c in palette if _color_distance(c["rgb"], bg_rgb) > 15]
    if text_candidates:
        best_text = max(text_candidates, key=lambda c: _contrast_ratio(c["hex"], colors["background"]))
    else:
        best_text = None

    if best_text:
        colors["text"] = best_text["hex"]
    else:
        colors["text"] = FALLBACK_TEXT_DARK if theme == "light" else FALLBACK_TEXT_LIGHT

    used_for_primary = {colors["background"].lower(), colors["text"].lower()}
    primary_candidates = [c for c in non_bg if not _is_neutral(c["rgb"], threshold=0.15)
                          and c["hex"].lower() not in used_for_primary]
    if primary_candidates:
        def primary_score(c):
            return _saturation(c["rgb"]) * 0.7 + c["ratio"] * 0.3
        primary = max(primary_candidates, key=primary_score)
        colors["primary"] = primary["hex"]
    elif non_bg:
        colors["primary"] = non_bg[0]["hex"]
    else:
        colors["primary"] = FALLBACK_PRIMARY

    surface_candidates = [c for c in neutrals if c["hex"].lower() != colors["background"].lower()]
    if surface_candidates:
        colors["surface"] = max(surface_candidates, key=lambda c: c["ratio"])["hex"]
    elif non_bg:
        def surface_score(c):
            lum_diff = abs(_relative_luminance(c["rgb"]) - _relative_luminance(bg_rgb))
            return lum_diff + c["ratio"]
        colors["surface"] = max(non_bg, key=surface_score)["hex"]
    else:
        colors["surface"] = "#f8f9fa" if theme == "light" else "#1e1e1e"

    used = {colors["primary"].lower(), colors["background"].lower(),
            colors["text"].lower(), colors["surface"].lower()}
    secondary_candidates = [
        c for c in non_bg
        if c["hex"].lower() not in used and not _is_neutral(c["rgb"], threshold=0.10)
    ]
    if secondary_candidates:
        secondary = max(secondary_candidates, key=lambda c: _saturation(c["rgb"]) + c["ratio"])
        colors["secondary"] = secondary["hex"]
    else:
        colors["secondary"] = FALLBACK_SECONDARY

    return colors


# ── 生成分析报告 ────────────────────────────────────────────────

def build_report(image_path: str, semantic_colors: Dict[str, str], palette: List[Dict], theme_info: Dict) -> Dict:
    """构建分析报告，含颜色、对比度、置信度。"""
    report = {
        "source": image_path,
        "theme": theme_info["theme"],
        "colors": dict(semantic_colors),
        "contrast_check": {},
        "confidence": {},
        "palette": palette[:6],
    }

    text = semantic_colors.get("text", FALLBACK_TEXT_LIGHT)
    bg = semantic_colors.get("background", FALLBACK_BACKGROUND)
    report["contrast_check"]["text_vs_bg"] = round(_contrast_ratio(text, bg), 2)

    primary = semantic_colors.get("primary", FALLBACK_PRIMARY)
    report["contrast_check"]["primary_vs_white"] = round(_contrast_ratio(primary, "#FFFFFF"), 2)

    palette_map = {c["hex"].lower(): c["ratio"] for c in palette}
    for name, hex_color in semantic_colors.items():
        report["confidence"][name] = round(palette_map.get(hex_color.lower(), 0) * 100, 1)

    notes = []
    primary_rgb = _hex_to_rgb(primary)
    if _is_neutral(primary_rgb, threshold=0.15):
        notes.append("Primary color appears neutral — may not be the brand color")
    if report["contrast_check"]["primary_vs_white"] < 4.5:
        notes.append("Primary color has low contrast against white")
    if notes:
        report["_notes"] = notes

    return report


# ── 生成 DESIGN.md ──────────────────────────────────────────────

def generate_design_md(report: Dict, output_path: str):
    """从分析报告生成 DESIGN.md。"""
    colors = report["colors"]
    theme = report["theme"]

    lines = ["---"]
    lines.append('version: "alpha"')
    lines.append(f'name: "Analyzed from {os.path.basename(report["source"])}"')
    lines.append('description: "Auto-extracted from screenshot analysis"')
    lines.append("")
    lines.append("# ===== Colors =====")
    lines.append("colors:")
    color_order = ["background", "surface", "primary", "secondary", "text", "error", "success", "warning", "info"]
    for k in color_order:
        if k in colors:
            lines.append(f'  {k}: "{colors[k]}"')
    for k, v in colors.items():
        if k not in color_order:
            lines.append(f'  {k}: "{v}"')
    lines.append("")
    lines.append("# ===== Analysis Info =====")
    lines.append("confidence:")
    for k, v in report["confidence"].items():
        lines.append(f"  {k}: {v}")
    lines.append("contrast_check:")
    for k, v in report["contrast_check"].items():
        lines.append(f"  {k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"Design tokens auto-extracted from screenshot: {os.path.basename(report['source'])}")
    lines.append("")
    lines.append(f"- **Theme**: {theme}")
    lines.append(f"- **Confidence**: primary={report['confidence'].get('primary', 0)}%")
    lines.append("")
    lines.append("> **Limitations**: Screenshot analysis estimates colors from pixel sampling.")
    lines.append("> It cannot detect semantic roles (what is a button vs background).")
    lines.append("> For live DOM sampling, delegate to designlang (`npx @designlang/cli`) and re-import via `--import`.")
    lines.append("")
    lines.append("## Colors")
    lines.append("")
    lines.append("| Token | Value | Confidence |")
    lines.append("|-------|-------|-----------|")
    for k in color_order:
        if k in colors:
            conf = report["confidence"].get(k, 0)
            lines.append(f"| **{k}** | {colors[k]} | {conf}% |")
    for k, v in colors.items():
        if k not in color_order:
            conf = report["confidence"].get(k, 0)
            lines.append(f"| **{k}** | {v} | {conf}% |")
    lines.append("")
    lines.append("## Contrast")
    lines.append("")
    lines.append(f"- **Text vs Background**: {report['contrast_check']['text_vs_bg']}:1")
    lines.append(f"- **Primary vs White**: {report['contrast_check']['primary_vs_white']}:1")
    lines.append("")

    notes = report.get("_notes", [])
    if notes:
        lines.append("## Quality Notes")
        lines.append("")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    content = "\n".join(lines) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"DESIGN.md generated from analysis: {output_path}")
    print(f"   Theme: {theme}")
    print(f"   Primary: {colors.get('primary', '?')}")
    print(f"   Confidence: primary={report['confidence'].get('primary', 0)}%")


# ── 主入口 ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Screenshot analysis engine — extract design tokens from images (colorthief + coloraide)"
    )
    parser.add_argument("image", help="screenshot image path")
    parser.add_argument("--output", "-o", default="DESIGN.md", help="output path")
    parser.add_argument("--colors", "-c", type=int, default=8, help="number of color clusters (default: 8)")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"错误：文件不存在 — {args.image}")
        sys.exit(1)

    if args.colors < 2 or args.colors > 20:
        print("错误：--colors 必须在 2-20 之间")
        sys.exit(1)

    print(f"Analyzing: {args.image}")
    palette = extract_palette(args.image, args.colors)
    theme_info = detect_theme(args.image)
    semantic = infer_semantic_colors(palette, theme_info["theme"])
    report = build_report(args.image, semantic, palette, theme_info)

    print(f"   Extracted {len(palette)} colors, theme={theme_info['theme']}")
    generate_design_md(report, args.output)

    json_path = args.output.replace(".md", "_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"   Analysis report: {json_path}")


if __name__ == "__main__":
    main()
