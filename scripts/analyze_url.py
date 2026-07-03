#!/usr/bin/env python3
"""Browser sampling engine v3 — Hardened Edition

Usage:
    python analyze_url.py https://example.com
    python analyze_url.py https://example.com --output DESIGN.md
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


EXTRACTION_JS = open(os.path.join(os.path.dirname(__file__), "extraction.js"), encoding="utf-8").read()


def validate_url(url: str) -> str:
    """校验 URL 格式，仅允许 http/https 协议。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"仅支持 http/https URL: {url}")
    if not parsed.netloc:
        raise ValueError(f"URL 格式不正确: {url}")
    return url


def _run_agent_browser_cmd(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """运行 agent-browser 命令，支持 npx 回退。"""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 and shutil.which("npx"):
        # 尝试 npx 回退
        npx_cmd = ["npx"] + cmd
        result = subprocess.run(npx_cmd, capture_output=True, text=True, timeout=timeout)
    return result


def _close_browser():
    """尽最大努力关闭浏览器实例。"""
    try:
        subprocess.run(["agent-browser", "close", "--all"],
                      capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def run_agent_browser(url: str, output_path: str = "") -> Dict[str, Any]:
    """Navigate to URL and extract design tokens via browser automation."""
    if not shutil.which("agent-browser") and not shutil.which("npx"):
        print("Error: agent-browser is not installed. Install with: npm install -g agent-browser")
        sys.exit(1)

    # 1. 打开页面
    result = _run_agent_browser_cmd(["agent-browser", "open", url], timeout=45)
    if result.returncode != 0:
        _close_browser()
        print(f"Error: failed to open {url}: {result.stderr[:300]}")
        sys.exit(1)

    # 2. 滚动并等待渲染
    _run_agent_browser_cmd(["agent-browser", "scroll", "down", "1000"], timeout=15)
    _run_agent_browser_cmd(["agent-browser", "wait", "2000"], timeout=15)

    # 3. 注入 JS 提取样式
    eval_result = ""
    result = _run_agent_browser_cmd(["agent-browser", "eval", EXTRACTION_JS, "--json"], timeout=30)
    eval_result = result.stdout

    if result.returncode != 0 or not eval_result:
        _close_browser()
        print(f"Error: failed to evaluate extraction script: {result.stderr[:300]}")
        sys.exit(1)

    # 4. 截图
    screenshot_path = os.path.abspath(output_path).replace(".md", "_screenshot.png") if output_path else os.path.abspath("page_design_tokens.png")
    try:
        subprocess.run(["agent-browser", "screenshot", screenshot_path],
                      capture_output=True, timeout=15)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 5. 关闭浏览器
    _close_browser()

    try:
        parsed = json.loads(eval_result)
    except json.JSONDecodeError as e:
        print(f"Parse error: {e}\n  eval stdout[:300]: {eval_result[:300]}")
        sys.exit(1)

    data = parsed
    if isinstance(parsed, dict):
        if "data" in parsed:
            inner = parsed["data"]
            if isinstance(inner, dict) and "result" in inner:
                raw = inner["result"]
                data = json.loads(raw) if isinstance(raw, str) else raw
            else:
                data = inner
    data["_screenshot"] = screenshot_path if os.path.exists(screenshot_path) else ""
    return data


def frequency_sort(items: List[str], top_n: int = 10) -> List[str]:
    """Return items sorted by frequency (most common first)."""
    return [item for item, _ in Counter(items).most_common(top_n)]


def _is_valid_hex(c: str) -> bool:
    return bool(re.match(r'^#[0-9a-fA-F]{3,8}$', c))


def _is_dark(hex_color: str) -> bool:
    h = hex_color.lstrip("#")
    if len(h) < 6:
        h = h.ljust(6, "0")
    return sum(int(h[i:i+2], 16) for i in (0, 2, 4)) / 3 < 128


def _contrast_ratio(c1: str, c2: str) -> float:
    def lum(rgb):
        def lin(v):
            v = v / 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = rgb
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    def parse(hex_c):
        h = hex_c.lstrip("#")
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) < 6:
            h = h.ljust(6, "0")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    try:
        l1, l2 = lum(parse(c1)), lum(parse(c2))
    except ValueError:
        return 1.0
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _normalize_color(c: str) -> Optional[str]:
    """将 CSS 颜色值归一化为 #RRGGBB。"""
    if not c:
        return None
    c = c.strip()
    if c.lower() == "transparent":
        return None
    if c.startswith("#"):
        if _is_valid_hex(c):
            h = c.lstrip("#")
            if len(h) in (3, 4):
                h = "".join(ch * 2 for ch in h)
            return f"#{h.lower()[:6]}"
        return None
    # rgb/rgba
    m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', c)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if all(0 <= v <= 255 for v in (r, g, b)):
            return f"#{r:02x}{g:02x}{b:02x}"
    return None


def analyze_extracted(data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Analyze extracted data to infer design tokens."""
    all_colors = data.get("colors", [])
    text_colors = data.get("textColors", [])
    bg_colors = data.get("bgColors", [])
    brand_colors = data.get("brandColors", [])
    body = data.get("body", {})
    font_sizes = data.get("fontSizes", [])
    css_vars = data.get("cssVars", {})
    pixel_samples = data.get("pixelSamples", {})

    result = {
        "source_url": url,
        "colors": {},
        "typography": {},
        "rounded": {},
        "elements_sampled": len(data.get("elements", [])),
        "total_unique_colors": len(all_colors),
        "palette": frequency_sort(all_colors, 15),
        "cssVars": css_vars,
    }

    # --- Primary color ---
    css_primary_keys = ["--primary", "--brand", "--accent", "--primary-color"]
    css_primary = None
    for k in css_primary_keys:
        v = css_vars.get(k, "")
        if v:
            css_primary = _normalize_color(v.strip())
            if css_primary:
                break

    pixel_primary = _normalize_color(pixel_samples.get("buttonColor", ""))
    normalized_brand = [_normalize_color(c) for c in brand_colors]
    normalized_brand = [c for c in normalized_brand if c and c.lower() not in ("#000000", "#ffffff")]

    if css_primary:
        result["colors"]["primary"] = css_primary
    elif normalized_brand:
        result["colors"]["primary"] = frequency_sort(normalized_brand, 3)[0]
    elif pixel_primary and pixel_primary.lower() != "#000000":
        result["colors"]["primary"] = pixel_primary
    elif all_colors:
        def saturation(c):
            c = _normalize_color(c)
            if not c:
                return 0
            h = c.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            mx, mn = max(r, g, b), min(r, g, b)
            return (mx - mn) / mx if mx > 0 else 0
        neutral = {"#000000", "#ffffff", "#fff", "#000"}
        saturated = sorted([c for c in all_colors if _normalize_color(c) and _normalize_color(c) not in neutral],
                          key=saturation, reverse=True)
        result["colors"]["primary"] = _normalize_color(saturated[0]) if saturated else FALLBACK_PRIMARY
    else:
        result["colors"]["primary"] = FALLBACK_PRIMARY

    # --- Background ---
    html_bg = None
    for el in data.get("elements", []):
        if el.get("tag") == "html" and el.get("bg"):
            html_bg = _normalize_color(el["bg"])
            break
    body_bg = _normalize_color(body.get("backgroundColor", ""))

    def is_plausible_bg(c):
        return c and c.lower() != "#000000"  # 避免纯黑误判

    if html_bg and is_plausible_bg(html_bg):
        result["colors"]["background"] = html_bg
    elif body_bg and is_plausible_bg(body_bg):
        result["colors"]["background"] = body_bg
    else:
        result["colors"]["background"] = "#FFFFFF"

    # --- Text color ---
    bg = result["colors"]["background"]
    normalized_text = [_normalize_color(c) for c in text_colors]
    normalized_text = [c for c in normalized_text if c and c.lower() != bg.lower() and c.lower() not in ("#000000", "#ffffff")]
    if normalized_text:
        best = max(normalized_text, key=lambda c: _contrast_ratio(c, bg))
        result["colors"]["text"] = best
    else:
        body_color = _normalize_color(body.get("color", ""))
        if body_color and body_color != bg:
            result["colors"]["text"] = body_color
        else:
            result["colors"]["text"] = FALLBACK_TEXT_DARK if _is_dark(bg) else FALLBACK_TEXT_LIGHT

    # --- Secondary color ---
    primary = result["colors"]["primary"]
    used = {primary.lower(), bg.lower(), result["colors"]["text"].lower()}
    other_colors = [_normalize_color(c) for c in all_colors]
    other_colors = [c for c in other_colors if c and c.lower() not in used and c.lower() not in ("#000000", "#ffffff")]
    if other_colors:
        result["colors"]["secondary"] = frequency_sort(other_colors, 1)[0]
    else:
        result["colors"]["secondary"] = FALLBACK_SECONDARY

    # --- Theme ---
    result["theme"] = "dark" if _is_dark(result["colors"]["background"]) else "light"

    # --- Typography ---
    fonts = list(set(data.get("fonts", [])))
    css_font_keys = ["--font-family", "--font-sans"]
    css_font = None
    for k in css_font_keys:
        v = css_vars.get(k, "")
        if v:
            css_font = v.strip()
            break
    if css_font:
        result["typography"]["fontFamily"] = css_font
    elif fonts:
        system_fonts = {"sans-serif", "serif", "monospace", "system-ui"}

        def font_score(f):
            f_lower = f.lower()
            if any(kw in f_lower for kw in ["sans", "inter", "sohne", "sf pro", "system-ui"]):
                return 2
            if any(kw in f_lower for kw in ["serif", "times", "georgia"]):
                return 1
            if any(kw in f_lower for kw in ["mono", "code", "fira code", "jetbrains"]):
                return 0
            return 1
        scored = sorted([f for f in fonts if f.lower() not in system_fonts], key=font_score, reverse=True)
        result["typography"]["fontFamily"] = scored[0] if scored else fonts[0]

    size_groups = {"heading": [], "body": [], "small": []}
    for fs in font_sizes:
        sz = fs.get("size", "16px")
        try:
            px = float(sz.replace("px", ""))
        except ValueError:
            continue
        tag = fs.get("tag", "div")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") or px >= 20:
            size_groups["heading"].append(px)
        elif px <= 13:
            size_groups["small"].append(px)
        else:
            size_groups["body"].append(px)

    for group, values in size_groups.items():
        if values:
            avg = round(sum(values) / len(values), 1)
            result["typography"][f"{group}Size"] = f"{avg}px"

    # --- Rounded corners ---
    standard_rounded = []
    for rv in data.get("rounded", []):
        if re.match(r'^\d+px$', rv):
            val = int(rv.replace("px", ""))
            if val > 0:
                standard_rounded.append(val)
    standard_rounded = sorted(set(standard_rounded))
    level_names = ["none", "sm", "md", "lg", "xl", "2xl", "3xl"]
    for i, val in enumerate(standard_rounded[:7]):
        name = level_names[i] if i < len(level_names) else f"level_{i+1}"
        result["rounded"][name] = f"{val}px"

    # Quality notes
    notes = []
    primary = result["colors"].get("primary", "")
    if primary:
        h = primary.lstrip("#")
        if len(h) >= 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            mx, mn = max(r, g, b), min(r, g, b)
            s = (mx - mn) / mx if mx > 0 else 0
            if s < 0.15:
                notes.append(f"Low saturation ({s:.2f}) — primary may be gray, not brand color")
    if _contrast_ratio(primary, "#FFFFFF") < 4.5:
        notes.append("Primary color has low contrast against white")
    if notes:
        result["_notes"] = notes

    return result


def generate_design_md(analysis: Dict[str, Any], output_path: str):
    """Generate a minimal DESIGN.md from browser-sampled tokens."""
    colors = analysis.get("colors", {})
    theme = analysis.get("theme", "light")
    lines = [
        "---",
        'version: "alpha"',
        f'name: "Sampled from {analysis.get("source_url", "?")}"',
        'description: "Extracted via browser sampling"',
        "",
        "# ===== Colors =====",
        "colors:",
    ]
    for k, v in colors.items():
        lines.append(f'  {k}: "{v}"')
    lines.append("---\n")
    lines.append("## Overview\n")
    lines.append(f"Design tokens sampled from {analysis.get('source_url', '?')}")
    lines.append(f"- **Theme**: {theme}")
    lines.append(f"- **Elements sampled**: {analysis.get('elements_sampled', 0)}")
    lines.append(f"- **Unique colors found**: {analysis.get('total_unique_colors', 0)}")
    notes = analysis.get("_notes", [])
    if notes:
        lines.append("")
        lines.append("### Quality Notes")
        for n in notes:
            lines.append(f"- {n}")
    lines.append("")

    css_vars = analysis.get("cssVars", {})
    if css_vars:
        lines.append("### Detected CSS Variables")
        names = ["--primary", "--brand", "--accent", "--primary-color", "--secondary", "--secondary-color",
                 "--text-color", "--bg-color", "--background-color", "--surface-color",
                 "--font-family", "--font-sans", "--radius", "--spacing"]
        for name in names:
            v = css_vars.get(name)
            if v:
                lines.append(f"- `{name}`: {v}")
        lines.append("")

    lines.append("> **Note**: Auto-extracted. Verify before production use.")
    lines.append("")
    lines.append("## Colors\n")
    lines.append("| Token | Value |")
    lines.append("|-------|-------|")
    for k, v in colors.items():
        lines.append(f"| **{k}** | {v} |")

    if analysis.get("typography"):
        lines.append("\n## Typography\n")
        for k, v in analysis["typography"].items():
            lines.append(f"- **{k}**: {v}")

    if analysis.get("rounded"):
        lines.append("\n## Shapes\n")
        for k, v in analysis["rounded"].items():
            lines.append(f"- **{k}**: {v}")

    lines.append("")
    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description="Browser sampling engine v3")
    parser.add_argument("url", help="target URL")
    parser.add_argument("--output", "-o", default="DESIGN.md")
    args = parser.parse_args()

    try:
        url = validate_url(args.url)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    print(f"Sampling: {url}")
    data = run_agent_browser(url, args.output)
    analysis = analyze_extracted(data, url)
    generate_design_md(analysis, args.output)

    print(f"DESIGN.md: {args.output}")
    print(f"   Theme: {analysis.get('theme', '?')}")
    print(f"   Primary: {analysis['colors'].get('primary', '?')}")
    print(f"   Elements: {analysis.get('elements_sampled', 0)}")
    print(f"   Unique colors: {analysis.get('total_unique_colors', 0)}")
    print(f"   Font: {analysis.get('typography', {}).get('fontFamily', '?')}")


if __name__ == "__main__":
    main()
