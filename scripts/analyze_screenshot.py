#!/usr/bin/env python3
"""截图分析引擎 — Hardened Edition

从 screenshot 提取设计令牌，输出 DESIGN.md 格式的设计令牌，含置信度标注。

通过 Pillow + sklearn 做颜色聚类、布局分析、主题检测。
改进点：
  - 修复 KMeans 失败路径的崩溃
  - 改进颜色语义推断（primary/background/text/surface）
  - 所有语义色附带置信度
  - 3 位 hex 安全处理
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageStat
from sklearn.cluster import MiniBatchKMeans


# ── 常量 ───────────────────────────────────────────────────────

FALLBACK_PRIMARY = "#1A73E8"
FALLBACK_SECONDARY = "#34A853"
FALLBACK_BACKGROUND = "#FFFFFF"
FALLBACK_TEXT_DARK = "#1A1C1E"
FALLBACK_TEXT_LIGHT = "#E8EAED"


# ── 颜色工具 ────────────────────────────────────────────────────

def _clamp(v: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, v))


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) < 6:
        h = h.ljust(6, "0")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{int(_clamp(r, 0, 255)):02x}{int(_clamp(g, 0, 255)):02x}{int(_clamp(b, 0, 255)):02x}"


def _srgb_linear(c: float) -> float:
    c = _clamp(c / 255.0)
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = (_srgb_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _is_dark(hex_color: str) -> bool:
    return _relative_luminance(_hex_to_rgb(hex_color)) < 0.179


def _contrast_ratio(c1: str, c2: str) -> float:
    try:
        l1 = _relative_luminance(_hex_to_rgb(c1))
        l2 = _relative_luminance(_hex_to_rgb(c2))
    except ValueError:
        return 1.0
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


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


# ── 颜色聚类 ────────────────────────────────────────────────────

def extract_palette(image_path: str, n_colors: int = 10) -> List[Dict]:
    """用 MiniBatchKMeans 提取主色调，跳过渐变/纹理区域。"""
    try:
        img = Image.open(image_path).convert("RGB")
    except (IOError, OSError) as e:
        print(f"错误：无法打开图片 — {image_path}: {e}")
        sys.exit(1)

    img.thumbnail((2000, 2000))
    w, h = img.size

    samples = []
    step = max(3, min(w, h) // 60)
    for y in range(0, h, step):
        for x in range(0, w, step):
            px = img.getpixel((x, y))
            if 4 < x < w - 4 and 4 < y < h - 4:
                neighbors = [
                    img.getpixel((x + 4, y)),
                    img.getpixel((x - 4, y)),
                    img.getpixel((x, y + 4)),
                    img.getpixel((x, y - 4)),
                ]
                var = sum(abs(px[i] - n[i]) for n in neighbors for i in range(3))
                if var < 80:
                    samples.append(px)
            else:
                samples.append(px)

    if len(samples) < 50:
        img.thumbnail((200, 200))
        samples = np.array(img).reshape(-1, 3).tolist()

    pixels = np.array(samples).astype(int)
    n_colors = min(n_colors, len(np.unique(pixels, axis=0)))
    if n_colors < 2:
        n_colors = 2

    try:
        kmeans = MiniBatchKMeans(n_clusters=n_colors, random_state=0, batch_size=1000)
        kmeans.fit(pixels)
        cluster_colors = kmeans.cluster_centers_.astype(int)
        labels = kmeans.labels_
    except (ValueError, np.linalg.LinAlgError) as e:
        print(f"Warning: KMeans failed ({e}), using frequency-based fallback")
        unique, counts = np.unique(pixels, axis=0, return_counts=True)
        top = sorted(zip(unique, counts), key=lambda x: x[1], reverse=True)[:n_colors]
        cluster_colors = np.array([c for c, _ in top])
        labels = np.zeros(len(pixels), dtype=int)
        for idx, (color, _) in enumerate(top):
            labels[(pixels == color).all(axis=1)] = idx

    counts = Counter(labels)
    sorted_indices = [i for i, _ in counts.most_common()]

    result = []
    for idx in sorted_indices:
        r, g, b = cluster_colors[idx]
        result.append({
            "hex": _rgb_to_hex(r, g, b),
            "rgb": (int(r), int(g), int(b)),
            "pixels": counts[idx],
            "ratio": round(counts[idx] / len(labels), 3),
        })
    return result


# ── 主题检测 ────────────────────────────────────────────────────

def detect_theme(image_path: str) -> Dict[str, str]:
    """检测浅色/深色主题，使用中位数亮度提高鲁棒性。"""
    img = Image.open(image_path).convert("L")
    stat = ImageStat.Stat(img)
    median_luminance = stat.median[0]
    avg_luminance = stat.mean[0]
    # 综合均值与中位数，避免大面积高亮/暗部干扰
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

    # Background: 最可能是大面积底色的颜色
    # 优先选择中性色中占比最高的；如果没有，选择占比最高的
    neutrals = [c for c in palette if _is_neutral(c["rgb"])]
    if neutrals:
        bg = max(neutrals, key=lambda c: c["ratio"])
    else:
        bg = max(palette, key=lambda c: c["ratio"])
    colors["background"] = bg["hex"]

    # 剩余候选（排除背景近似色）
    bg_rgb = bg["rgb"]

    def near_bg(c):
        return _color_distance(c["rgb"], bg_rgb) < 25

    non_bg = [c for c in palette if not near_bg(c)]

    # Text: 与背景对比度最高，排除背景本身及近背景色
    def usable_for_text(c):
        return _color_distance(c["rgb"], bg_rgb) > 15

    text_candidates = [c for c in palette if usable_for_text(c)]
    if text_candidates:
        best_text = max(text_candidates, key=lambda c: _contrast_ratio(c["hex"], colors["background"]))
    else:
        best_text = None

    if best_text:
        colors["text"] = best_text["hex"]
    else:
        colors["text"] = FALLBACK_TEXT_DARK if theme == "light" else FALLBACK_TEXT_LIGHT

    # Primary: 非中性、饱和度最高、且不是文字色
    used_for_primary = {colors["background"].lower(), colors["text"].lower()}
    primary_candidates = [c for c in non_bg if not _is_neutral(c["rgb"], threshold=0.15)
                          and c["hex"].lower() not in used_for_primary]
    if primary_candidates:
        # 综合饱和度与像素占比：避免极小块高饱和噪点
        def primary_score(c):
            return _saturation(c["rgb"]) * 0.7 + c["ratio"] * 0.3
        primary = max(primary_candidates, key=primary_score)
        colors["primary"] = primary["hex"]
    elif non_bg:
        colors["primary"] = non_bg[0]["hex"]
    else:
        colors["primary"] = FALLBACK_PRIMARY

    # Surface: 第二常见的中性/近中性色，且不是背景
    surface_candidates = [c for c in neutrals if c["hex"].lower() != colors["background"].lower()]
    if surface_candidates:
        colors["surface"] = max(surface_candidates, key=lambda c: c["ratio"])["hex"]
    elif non_bg:
        # 选择亮度与背景有明显差异的颜色
        def surface_score(c):
            lum_diff = abs(_relative_luminance(c["rgb"]) - _relative_luminance(bg_rgb))
            return lum_diff + c["ratio"]
        colors["surface"] = max(non_bg, key=surface_score)["hex"]
    else:
        colors["surface"] = "#f8f9fa" if theme == "light" else "#1e1e1e"

    # Secondary: 与 primary/background/text/surface 都不同的颜色
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

    # 置信度：基于像素占比
    palette_map = {c["hex"].lower(): c["ratio"] for c in palette}
    for name, hex_color in semantic_colors.items():
        report["confidence"][name] = round(palette_map.get(hex_color.lower(), 0) * 100, 1)

    # 质量备注
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
    lines.append(f"")
    lines.append(f"- **Theme**: {theme}")
    lines.append(f"- **Confidence**: primary={report['confidence'].get('primary', 0)}%")
    lines.append("")
    lines.append("> **Limitations**: Screenshot analysis estimates colors from pixel sampling.")
    lines.append("> It cannot detect semantic roles (what is a button vs background).")
    lines.append("> For better accuracy, use `--analyze-url` for live browser sampling.")
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
        description="Screenshot analysis engine — extract design tokens from images"
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
