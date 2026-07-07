#!/usr/bin/env python3
"""DESIGN.md 设计规范生成器 — Hardened Edition

根据品牌信息自动生成符合 google-labs-code/design.md 规范的 DESIGN.md 文件。
兼容 CSS 颜色格式，包含机器可读的 YAML 令牌和人类可读的 Markdown 正文。

防护体系:
  P0: 严格输入校验 + YAML 注入防护 + WCAG 对比度检测 + 原子写入 + 路径遍历防护
  P1: 深色主题完整适配 + 行业模板预设 + 版本化输出 + 渐进式交互
  P2: 色板可视化(SVG) + 迭代修改(重新生成以保持派生色一致) + 中文字体自动匹配

Usage:
    python generate_design_spec.py --name "Brand" [options]
    python generate_design_spec.py --name "Brand" --template ecommerce
    python generate_design_spec.py --name "Brand" --theme dark --background "#1A1C1E"
    python generate_design_spec.py --name "Brand" --visualize
    python generate_design_spec.py --modify DESIGN.md --set "primary=#FF0000"
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from coloraide import Color as CColor

ANALYSIS_SCRIPT = os.path.join(os.path.dirname(__file__), "analyze_screenshot.py")


# ═══════════════════════════════════════════════════════════════
# 常量与配置
# ═══════════════════════════════════════════════════════════════

VALID_TONES = ["专业", "活泼", "极简", "科技", "优雅"]
VALID_TEMPLATES = [
    # 原 12 个
    "enterprise", "ecommerce", "finance", "creative",
    "healthcare", "education", "gaming", "food-beverage",
    "real-estate", "travel", "social-media", "developer-tools",
    # 新增 38+ 个
    # AI / SaaS 细分
    "ai-assistant", "saas-analytics", "crm", "devops",
    "nocode", "cybersecurity", "cloud-infra",
    # 区块链 / Web3
    "blockchain", "crypto-wallet", "nft-marketplace", "defi",
    # 媒体 / 内容
    "streaming", "podcast", "news-portal", "blog-platform",
    "photography", "animation-studio",
    # 健身 / 健康
    "fitness", "wellness", "meditation",
    # 美容 / 时尚
    "beauty", "cosmetics", "fashion",
    # 法律 / 政务
    "legal", "government", "nonprofit",
    # 教育细分
    "k12-education", "corporate-training", "language-learning",
    # 房地产细分
    "commercial-real-estate", "interior-design",
    # 物流 / 制造
    "logistics", "manufacturing", "agriculture", "energy",
    # 专业服务
    "consulting", "hr-recruiting", "event-management",
    # 娱乐 / 生活方式
    "dating", "pet-care", "parenting", "music-production",
]

DEFAULT_PRIMARY = "#1A73E8"
DEFAULT_SECONDARY = "#34A853"
DEFAULT_BACKGROUND = "#FFFFFF"
DEFAULT_TEXT_LIGHT = "#1A1C1E"
DEFAULT_TEXT_DARK = "#E8EAED"
DEFAULT_FONT = "Inter, system-ui, sans-serif"
DEFAULT_CJK_FONT = "'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', system-ui, sans-serif"
DEFAULT_MONO_FONT = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace"

# 字段级默认回退值
FIELD_DEFAULTS = {
    "primary": DEFAULT_PRIMARY,
    "secondary": DEFAULT_SECONDARY,
    "background": DEFAULT_BACKGROUND,
    "text": DEFAULT_TEXT_LIGHT,
}

# CSS 颜色解析统一委托 coloraide（见 normalize_to_hex），此处不再维护手写正则。


class ValidationError(Exception):
    """用户输入校验失败。"""
    pass


@dataclass
class ColorTheme:
    """一次生成任务中使用的完整颜色配置。"""
    primary: str
    secondary: str
    background: str
    text: str
    is_dark: bool
    surface: str = ""
    surface_hover: str = ""
    text_secondary: str = ""
    text_disabled: str = ""
    border: str = ""
    divider: str = ""


# ═══════════════════════════════════════════════════════════════
# 警告收集（按实例隔离，避免多次调用累积）
# ═══════════════════════════════════════════════════════════════

class WarningCollector:
    def __init__(self):
        self._items: List[str] = []
        self._seen = set()

    def add(self, message: str):
        if message not in self._seen:
            self._items.append(message)
            self._seen.add(message)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def list(self) -> List[str]:
        return list(self._items)


WARNINGS = WarningCollector()


# ═══════════════════════════════════════════════════════════════
# P0-1: 颜色解析与输入校验
# ═══════════════════════════════════════════════════════════════

def normalize_to_hex(color_val: str) -> str:
    """将任意受支持的 CSS 颜色归一化为 6 位小写 hex。

    委托 coloraide（完整支持 CSS Color Level 4：hex / rgb / hsl /
    oklch / oklab / hwb / transparent / 命名色），不再手写解析。
    """
    if not isinstance(color_val, str):
        raise ValueError(f"颜色必须是字符串，收到 {type(color_val).__name__}")
    original = color_val.strip()
    if not original:
        raise ValueError("颜色不能为空")
    c = original.lower()
    if c == "transparent":
        return "#FFFFFF"
    try:
        col = CColor(c)
        return col.convert("srgb").to_string(hex=True, alpha=False)
    except Exception:
        raise ValueError(f"不支持的 CSS 颜色格式: {original}")


def validate_color(value: str, label: str) -> str:
    """校验颜色值并归一化为 hex。非法时按字段回退默认值并记录警告。"""
    if not value or not isinstance(value, str) or not value.strip():
        default = FIELD_DEFAULTS.get(label, DEFAULT_PRIMARY)
        WARNINGS.add(f"[{label}] 为空，使用默认值 {default}")
        return default
    try:
        return normalize_to_hex(value)
    except ValueError as e:
        default = FIELD_DEFAULTS.get(label, DEFAULT_PRIMARY)
        WARNINGS.add(f"[{label}] 格式非法（{value}）: {e}，使用默认值 {default}")
        return default


# ═══════════════════════════════════════════════════════════════
# P0-2: YAML 注入防护
# ═══════════════════════════════════════════════════════════════

def escape_yaml(value: str) -> str:
    """对写入双引号 YAML 标量的字符串进行安全转义。"""
    if not isinstance(value, str):
        value = str(value)
    # 将真实的换行与回车替换为空格，避免多行字符串破坏 YAML 结构
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # 也将用户传入的 \\n / \\r 字面序列替换为空格
    value = value.replace("\\n", " ").replace("\\r", " ")
    # 移除行首 YAML 控制字符
    value = re.sub(r'^[\s\-?:,\[\]{}&#*!|>%@`]', '', value, flags=re.MULTILINE)
    # 移除空字符与方向控制字符
    value = value.replace("\x00", "").replace("\x0b", "").replace("\x0c", "")
    value = re.sub(r'[\u202a-\u202e\u2066-\u2069]', '', value)
    # 转义反斜杠与双引号（放在最后，避免影响前面的处理）
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return value.strip()


# ═══════════════════════════════════════════════════════════════
# P0-3: WCAG 对比度检测
# ═══════════════════════════════════════════════════════════════

def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    return CColor("rgb({}, {}, {})".format(*rgb)).luminance()


def contrast_ratio(c1: str, c2: str) -> float:
    try:
        return CColor(normalize_to_hex(c1)).contrast(
            CColor(normalize_to_hex(c2)), method="wcag21"
        )
    except Exception:
        return 1.0


def check_contrast_pairs(pairs: List[Tuple[str, str, str, str]], label: str):
    for fg_name, bg_name, fg, bg in pairs:
        ratio = contrast_ratio(fg, bg)
        if ratio < 4.5:
            suggestion = _suggest_contrast_color(fg, bg)
            WARNINGS.add(
                f"[对比度] {label}/{fg_name} 与 {bg_name} 的对比度为 {ratio:.2f}:1"
                f"，不满足 WCAG AA 标准(4.5:1){suggestion}"
            )


def _suggest_contrast_color(fg: str, bg: str) -> str:
    """生成对比度改进建议（沿 oklch 向黑/白插值至满足 WCAG AA）。"""
    try:
        bgc = CColor(normalize_to_hex(bg))
        fgc = CColor(normalize_to_hex(fg))
    except Exception:
        return ""
    if bgc.contrast(fgc, method="wcag21") >= 4.5:
        return ""
    target = CColor("#FFFFFF") if is_dark_bg(bg) else CColor("#000000")
    interp = fgc.interpolate([target], space="oklch")
    for step in range(1, 21):
        t = step / 20.0
        cand = interp(t)
        if bgc.contrast(cand, method="wcag21") >= 4.5:
            suggested = cand.convert("srgb").to_string(hex=True, alpha=False)
            ratio = bgc.contrast(cand, method="wcag21")
            return f"，建议改用 {suggested}（对比度可达 {ratio:.1f}:1）"
    return "，建议加深或提亮前景色"


# ═══════════════════════════════════════════════════════════════
# 颜色工具
# ═══════════════════════════════════════════════════════════════

def lighten_color(color_val: str, factor: float = 0.15) -> str:
    if not color_val:
        return "#F5F5F5"
    try:
        c = CColor(normalize_to_hex(color_val)).convert("oklch")
        c.set("l", min(1.0, c.get("l") + factor))
        return c.convert("srgb").to_string(hex=True, alpha=False)
    except Exception:
        return "#F5F5F5"


def darken_color(color_val: str, factor: float = 0.15) -> str:
    if not color_val:
        return "#CCCCCC"
    try:
        c = CColor(normalize_to_hex(color_val)).convert("oklch")
        c.set("l", max(0.0, c.get("l") - factor))
        return c.convert("srgb").to_string(hex=True, alpha=False)
    except Exception:
        return "#CCCCCC"


def relative_luminance_value(color_val: str) -> float:
    try:
        return CColor(normalize_to_hex(color_val)).luminance()
    except Exception:
        return 1.0


def is_dark_bg(color_val: str) -> bool:
    """使用相对亮度判断背景深浅（阈值 0.179，对应 #BFBFBF 附近）。"""
    return relative_luminance_value(color_val) < 0.179


def auto_text_color(bg_color: str) -> str:
    """根据背景色自动选择对比度合适的文字色。"""
    return DEFAULT_TEXT_DARK if is_dark_bg(bg_color) else DEFAULT_TEXT_LIGHT


# ═══════════════════════════════════════════════════════════════
# P1-2: 模板预设
# ═══════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, dict] = {
    # ═══════════════════════════════════════
    # 原 12 个模板（保持兼容）
    # ═══════════════════════════════════════
    "enterprise": {
        "name": "Enterprise", "primary": "#1A73E8", "secondary": "#34A853",
        "background": "#FFFFFF", "text": "#1A1C1E", "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向企业级 SaaS 与 B2B 产品的专业设计系统",
        "anti_patterns": ["避免使用过于鲜艳的强调色", "不要使用圆润的卡通风格"],
    },
    "ecommerce": {
        "name": "E-Commerce", "primary": "#C2185B", "secondary": "#FF9800",
        "background": "#FFFFFF", "text": "#212121", "font": DEFAULT_CJK_FONT,
        "tone": "活泼",
        "desc": "面向电商促销与营销页面的视觉冲击力设计系统",
        "anti_patterns": ["避免信息密度过低", "促销标签不要使用接近主色的色调"],
    },
    "finance": {
        "name": "Finance", "primary": "#0A753D", "secondary": "#1565C0",
        "background": "#F8F9FA", "text": "#1A1C1E",
        "font": "'SF Pro Text', Inter, system-ui, sans-serif",
        "tone": "专业",
        "desc": "面向银行、理财、支付场景的稳健可信设计系统",
        "anti_patterns": ["避免使用紫色/粉色渐变", "不要使用过多圆角保持严肃感"],
    },
    "creative": {
        "name": "Creative", "primary": "#9C27B0", "secondary": "#FF5722",
        "background": "#0D0D0D", "text": "#E8EAED",
        "font": "'GT America', Inter, system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向娱乐、短视频、内容创作的潮流设计系统",
        "anti_patterns": ["避免使用低对比度的柔和色", "不要让文字可读性让步于视觉效果"],
    },
    "healthcare": {
        "name": "Healthcare", "primary": "#0E7490", "secondary": "#06B6D4",
        "background": "#F0FDFA", "text": "#0F172A", "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向医疗健康、在线问诊、药房管理的安心设计系统",
        "anti_patterns": ["避免红色为主色（易与紧急/错误混淆）", "保持高对比度确保可读性"],
    },
    "education": {
        "name": "Education", "primary": "#EA580C", "secondary": "#F59E0B",
        "background": "#FFFBEB", "text": "#1E293B", "font": DEFAULT_CJK_FONT,
        "tone": "活泼",
        "desc": "面向在线教育、知识付费、学习平台的温暖设计系统",
        "anti_patterns": ["避免冷色调作为主色", "不要使用过于紧凑的排版"],
    },
    "gaming": {
        "name": "Gaming", "primary": "#7C3AED", "secondary": "#F43F5E",
        "background": "#0F0F23", "text": "#E2E8F0",
        "font": "'Inter', 'Manrope', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向游戏平台、电竞社区、互动娱乐的沉浸设计系统",
        "anti_patterns": ["避免低饱和度配色", "不要在深色背景上使用深紫色文字"],
    },
    "food-beverage": {
        "name": "Food & Beverage", "primary": "#DC2626", "secondary": "#F97316",
        "background": "#FFF7ED", "text": "#292524", "font": DEFAULT_CJK_FONT,
        "tone": "活泼",
        "desc": "面向餐饮外卖、食谱分享、食品品牌的食欲感设计系统",
        "anti_patterns": ["避免蓝色作为主色（抑制食欲）", "不要使用过小的字体展示菜单"],
    },
    "real-estate": {
        "name": "Real Estate", "primary": "#166534", "secondary": "#CA8A04",
        "background": "#F8FAFC", "text": "#0F172A", "font": DEFAULT_FONT,
        "tone": "优雅",
        "desc": "面向房产展示、物业管理的稳健可靠设计系统",
        "anti_patterns": ["避免过于花哨的渐变和装饰", "不要使用刺眼的亮色作为背景"],
    },
    "travel": {
        "name": "Travel", "primary": "#0284C7", "secondary": "#0EA5E9",
        "background": "#F0F9FF", "text": "#0F172A", "font": DEFAULT_FONT,
        "tone": "活泼",
        "desc": "面向旅游出行、酒店预订的自由感设计系统",
        "anti_patterns": ["避免暗色调为主", "不要在目的地卡片上使用低对比度文字"],
    },
    "social-media": {
        "name": "Social Media", "primary": "#EC4899", "secondary": "#8B5CF6",
        "background": "#FAFAFA", "text": "#18181B", "font": DEFAULT_FONT,
        "tone": "活泼",
        "desc": "面向社交平台、社区论坛、内容分享的活力设计系统",
        "anti_patterns": ["避免过于正式的排版风格", "不要让操作按钮太小不易点击"],
    },
    "developer-tools": {
        "name": "Developer Tools", "primary": "#0F766E", "secondary": "#6366F1",
        "background": "#0A0A0A", "text": "#E4E4E7",
        "font": "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
        "tone": "科技",
        "desc": "面向开发者工具、API 文档、技术产品的极客设计系统",
        "anti_patterns": ["避免低信息密度布局", "不要在深色背景上使用灰色文字"],
    },
    # ═══════════════════════════════════════
    # 新增 38 个模板
    # ═══════════════════════════════════════
    "ai-assistant": {
        "name": "AI Assistant", "primary": "#6366F1", "secondary": "#A855F7",
        "background": "#FFFFFF", "text": "#1E293B",
        "font": "'SF Pro', Inter, system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向 AI 对话助手、Copilot 产品的智能设计系统",
        "anti_patterns": ["避免机器人感的冰冷配色", "不要让 AI 输出的区域与用户输入区域视觉混淆"],
    },
    "saas-analytics": {
        "name": "SaaS Analytics", "primary": "#2563EB", "secondary": "#7C3AED",
        "background": "#F8FAFC", "text": "#0F172A", "font": DEFAULT_FONT,
        "tone": "科技",
        "desc": "面向数据分析、商业智能仪表盘的数据密集型设计系统",
        "anti_patterns": ["避免过多颜色导致图表喧宾夺主", "不要让数据标签字号小于 12px"],
    },
    "crm": {
        "name": "CRM", "primary": "#0891B2", "secondary": "#0284C7",
        "background": "#FFFFFF", "text": "#1E293B", "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向客户关系管理、销售追踪的务实设计系统",
        "anti_patterns": ["避免过于休闲的配色", "不要让表格行高过小影响可读性"],
    },
    "devops": {
        "name": "DevOps", "primary": "#2563EB", "secondary": "#059669",
        "background": "#0F172A", "text": "#E2E8F0",
        "font": "'SF Mono', 'JetBrains Mono', monospace",
        "tone": "科技",
        "desc": "面向 CI/CD、监控告警、基础设施的运维设计系统",
        "anti_patterns": ["避免使用浅色作为背景", "状态指示色必须满足 WCAG AA"],
    },
    "nocode": {
        "name": "No-Code", "primary": "#E11D48", "secondary": "#F97316",
        "background": "#FFFFFF", "text": "#18181B",
        "font": "'Inter', 'DM Sans', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向无代码平台、自动化工具的用户友好设计系统",
        "anti_patterns": ["避免技术感太强（如终端风格）", "不要让拖拽区域视觉上难以识别"],
    },
    "cybersecurity": {
        "name": "Cybersecurity", "primary": "#059669", "secondary": "#0284C7",
        "background": "#0C0A09", "text": "#E7E5E4",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向安全监控、威胁检测的警惕感设计系统",
        "anti_patterns": ["避免使用过于明亮的色彩作为背景", "危险告警色必须使用红色系"],
    },
    "cloud-infra": {
        "name": "Cloud Infrastructure", "primary": "#2563EB", "secondary": "#D97706",
        "background": "#FAFAFA", "text": "#171717",
        "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向云服务控制台、资源管理的效率设计系统",
        "anti_patterns": ["避免信息密度过低", "不要让状态图标使用相近色"],
    },
    "blockchain": {
        "name": "Blockchain", "primary": "#F59E0B", "secondary": "#6366F1",
        "background": "#0A0A0A", "text": "#E5E7EB",
        "font": "'Inter', 'Space Grotesk', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向区块链浏览器、去中心化应用的未来感设计系统",
        "anti_patterns": ["避免使用政府/银行风格的蓝色", "不要使用过多渐变"],
    },
    "crypto-wallet": {
        "name": "Crypto Wallet", "primary": "#8B5CF6", "secondary": "#06B6D4",
        "background": "#09090B", "text": "#E4E4E7",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向加密货币钱包、DeFi 面板的安全设计系统",
        "anti_patterns": ["避免使用过于明亮的文字色", "资产数字必须使用等宽字体"],
    },
    "nft-marketplace": {
        "name": "NFT Marketplace", "primary": "#EC4899", "secondary": "#06B6D4",
        "background": "#0F0F0F", "text": "#E2E8F0",
        "font": "'Space Grotesk', Inter, system-ui, sans-serif",
        "tone": "极简",
        "desc": "面向 NFT 交易市场、数字藏品展示的沉浸设计系统",
        "anti_patterns": ["避免过多颜色冲突", "不要让卡片间距过小"],
    },
    "defi": {
        "name": "DeFi", "primary": "#10B981", "secondary": "#3B82F6",
        "background": "#0A0A0A", "text": "#FAFAFA",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向去中心化金融、流动性挖矿的数据设计系统",
        "anti_patterns": ["避免过于装饰性的视觉元素", "涨跌色必须符合各自市场惯例"],
    },
    "streaming": {
        "name": "Streaming", "primary": "#E50914", "secondary": "#000000",
        "background": "#141414", "text": "#FFFFFF",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "极简",
        "desc": "面向视频流媒体、直播平台的沉浸观看设计系统",
        "anti_patterns": ["避免在视频缩略图上叠加亮色 UI", "不要让控制栏自动隐藏过慢"],
    },
    "podcast": {
        "name": "Podcast", "primary": "#7C3AED", "secondary": "#10B981",
        "background": "#FAFAFA", "text": "#1C1917",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "优雅",
        "desc": "面向播客平台、音频内容的温暖设计系统",
        "anti_patterns": ["避免冷色作为主色", "不要让播放进度条过于纤细"],
    },
    "news-portal": {
        "name": "News Portal", "primary": "#1E293B", "secondary": "#DC2626",
        "background": "#FFFFFF", "text": "#111827",
        "font": "'PT Serif', 'Noto Serif SC', Georgia, serif",
        "tone": "专业",
        "desc": "面向新闻门户、媒体网站的可信设计系统",
        "anti_patterns": ["避免过度装饰和动画", "正文不要使用小于 16px 的字号"],
    },
    "blog-platform": {
        "name": "Blog Platform", "primary": "#292524", "secondary": "#D97706",
        "background": "#FCFCFC", "text": "#1C1917",
        "font": "'Noto Serif', Georgia, 'Times New Roman', serif",
        "tone": "优雅",
        "desc": "面向博客、个人写作的文字友好设计系统",
        "anti_patterns": ["避免过于花哨的界面元素", "不要让正文行宽超过 720px"],
    },
    "photography": {
        "name": "Photography", "primary": "#1A1A1A", "secondary": "#FAFAFA",
        "background": "#000000", "text": "#F5F5F5",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "极简",
        "desc": "面向摄影作品集、画廊展示的无干扰设计系统",
        "anti_patterns": ["避免在照片上叠加颜色", "不要让 UI 元素遮盖画面主体"],
    },
    "animation-studio": {
        "name": "Animation Studio", "primary": "#6366F1", "secondary": "#22D3EE",
        "background": "#0A0A0A", "text": "#E2E8F0",
        "font": "'DM Sans', Inter, system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向动画工作室、动态设计的创意设计系统",
        "anti_patterns": ["避免静态感过强的设计", "不要让过渡动画时间超过 500ms"],
    },
    "fitness": {
        "name": "Fitness", "primary": "#EA580C", "secondary": "#22C55E",
        "background": "#FAFAFA", "text": "#1C1917",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向健身追踪、运动训练的激励设计系统",
        "anti_patterns": ["避免使用冷色作为主色", "不要让数字显示小于 24px"],
    },
    "wellness": {
        "name": "Wellness", "primary": "#06B6D4", "secondary": "#A3E635",
        "background": "#F0F9FF", "text": "#0F172A",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "优雅",
        "desc": "面向健康管理、生活方式的舒缓设计系统",
        "anti_patterns": ["避免高对比度的颜色碰撞", "不要让动画过于急促"],
    },
    "meditation": {
        "name": "Meditation", "primary": "#8B5CF6", "secondary": "#A78BFA",
        "background": "#0F0A1E", "text": "#E9DFF5",
        "font": "'Inter', 'Noto Sans SC', system-ui, sans-serif",
        "tone": "极简",
        "desc": "面向冥想、正念应用的宁静设计系统",
        "anti_patterns": ["避免使用警示色（红/橙）", "不要让界面产生视觉紧迫感"],
    },
    "beauty": {
        "name": "Beauty", "primary": "#DB2777", "secondary": "#F472B6",
        "background": "#FFF1F2", "text": "#1F2937",
        "font": "'Playfair Display', 'Noto Serif SC', Georgia, serif",
        "tone": "优雅",
        "desc": "面向美妆护肤、个护品牌的精致设计系统",
        "anti_patterns": ["避免暗色调为主", "不要让产品图片被文字遮挡"],
    },
    "cosmetics": {
        "name": "Cosmetics", "primary": "#E11D48", "secondary": "#FDA4AF",
        "background": "#FFFFFF", "text": "#1E293B",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向化妆品、香水品牌的奢华设计系统",
        "anti_patterns": ["避免粗糙的纹理背景", "不要让价格标签过于显眼破坏高级感"],
    },
    "fashion": {
        "name": "Fashion", "primary": "#18181B", "secondary": "#F59E0B",
        "background": "#FAFAFA", "text": "#18181B",
        "font": "'Bodoni Moda', 'Noto Serif SC', Georgia, serif",
        "tone": "优雅",
        "desc": "面向时尚电商、穿搭平台的高级感设计系统",
        "anti_patterns": ["避免使用过多颜色", "不要让 UI 界面比服装图片更引人注目"],
    },
    "legal": {
        "name": "Legal", "primary": "#1E3A5F", "secondary": "#8B4513",
        "background": "#FDFBF7", "text": "#1A1A1A",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "专业",
        "desc": "面向律师事务所、法务管理的庄重设计系统",
        "anti_patterns": ["避免使用彩色渐变", "不要使用非衬线字体做正文"],
    },
    "government": {
        "name": "Government", "primary": "#1B4332", "secondary": "#4A5568",
        "background": "#F8F9FA", "text": "#1A202C",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "专业",
        "desc": "面向政务平台、公共服务的高可信设计系统",
        "anti_patterns": ["避免使用蓝色系作为强调色（与链接混淆）", "不要使用装饰性图形"],
    },
    "nonprofit": {
        "name": "Nonprofit", "primary": "#059669", "secondary": "#0EA5E9",
        "background": "#FFFFFF", "text": "#1E293B",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "优雅",
        "desc": "面向非营利组织、公益捐款的温暖设计系统",
        "anti_patterns": ["避免奢华感的设计元素", "不要让捐款按钮使用冷色调"],
    },
    "k12-education": {
        "name": "K-12 Education", "primary": "#F59E0B", "secondary": "#3B82F6",
        "background": "#FFFBEB", "text": "#1E293B", "font": DEFAULT_CJK_FONT,
        "tone": "活泼",
        "desc": "面向 K12 教育、少儿编程的友好设计系统",
        "anti_patterns": ["避免过于成熟的商务感", "不要让文字字号小于 16px"],
    },
    "corporate-training": {
        "name": "Corporate Training", "primary": "#6366F1", "secondary": "#22D3EE",
        "background": "#F8FAFC", "text": "#0F172A", "font": DEFAULT_FONT,
        "tone": "科技",
        "desc": "面向企业培训、员工发展的效率设计系统",
        "anti_patterns": ["避免过于幼稚的卡通风格", "不要让课程卡片信息密度过低"],
    },
    "language-learning": {
        "name": "Language Learning", "primary": "#10B981", "secondary": "#6366F1",
        "background": "#FFFFFF", "text": "#1E293B",
        "font": "'Inter', 'Noto Sans SC', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向语言学习、翻译工具的教育设计系统",
        "anti_patterns": ["避免使用红色作为纠错色外的强调色", "不要让生词卡片过大超出视图"],
    },
    "commercial-real-estate": {
        "name": "Commercial RE", "primary": "#92400E", "secondary": "#15803D",
        "background": "#FFFBEB", "text": "#1F2937", "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向商业地产投资、租赁的专业设计系统",
        "anti_patterns": ["避免过于花哨的装饰", "不要让数据表格过于紧凑"],
    },
    "interior-design": {
        "name": "Interior Design", "primary": "#D97706", "secondary": "#78716C",
        "background": "#FAFAF9", "text": "#1C1917",
        "font": "'Playfair Display', 'Noto Serif SC', serif",
        "tone": "优雅",
        "desc": "面向室内设计、家具展示的审美设计系统",
        "anti_patterns": ["避免过于鲜艳的颜色", "不要让 UI 界面比设计作品本身更引人注目"],
    },
    "logistics": {
        "name": "Logistics", "primary": "#2563EB", "secondary": "#D97706",
        "background": "#F8FAFC", "text": "#1E293B", "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向物流追踪、仓储管理的操作型设计系统",
        "anti_patterns": ["避免使用大面积的浅色背景", "不要让状态标签使用相近色"],
    },
    "manufacturing": {
        "name": "Manufacturing", "primary": "#475569", "secondary": "#2563EB",
        "background": "#F1F5F9", "text": "#0F172A",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "专业",
        "desc": "面向制造业 MES、工业 IoT 的工业设计系统",
        "anti_patterns": ["避免使用过于柔和的配色", "告警颜色必须符合工业安全标准"],
    },
    "agriculture": {
        "name": "Agriculture", "primary": "#15803D", "secondary": "#65A30D",
        "background": "#F7FEE7", "text": "#1A2E05",
        "font": DEFAULT_FONT,
        "tone": "优雅",
        "desc": "面向农业科技、智慧农场的大地色设计系统",
        "anti_patterns": ["避免使用城市感的蓝色/灰色", "不要使用过于细小的字体"],
    },
    "energy": {
        "name": "Energy", "primary": "#059669", "secondary": "#D97706",
        "background": "#ECFDF5", "text": "#064E3B",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向能源管理、碳中和的绿色设计系统",
        "anti_patterns": ["避免使用工业灰色调", "不要让绿色色阶过于单一"],
    },
    "consulting": {
        "name": "Consulting", "primary": "#1E3A5F", "secondary": "#D4AF37",
        "background": "#FFFFFF", "text": "#1E293B",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "专业",
        "desc": "面向管理咨询、战略服务的权威设计系统",
        "anti_patterns": ["避免过于休闲的设计元素", "不要让信息呈现层级混乱"],
    },
    "hr-recruiting": {
        "name": "HR & Recruiting", "primary": "#6366F1", "secondary": "#22D3EE",
        "background": "#FFFFFF", "text": "#1E293B", "font": DEFAULT_FONT,
        "tone": "专业",
        "desc": "面向人力资源、招聘平台的专业设计系统",
        "anti_patterns": ["避免使用过于冰冷的色调", "不要让职位卡片信息过少"],
    },
    "event-management": {
        "name": "Event Management", "primary": "#E11D48", "secondary": "#F59E0B",
        "background": "#FFF1F2", "text": "#1E293B",
        "font": "'Inter', 'DM Sans', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向活动策划、票务管理的活力设计系统",
        "anti_patterns": ["避免信息层级混乱", "不要让倒计时组件尺寸过小"],
    },
    "dating": {
        "name": "Dating", "primary": "#EC4899", "secondary": "#8B5CF6",
        "background": "#FFF0F5", "text": "#1F2937",
        "font": "'Inter', 'DM Sans', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向社交约会、交友平台的浪漫设计系统",
        "anti_patterns": ["避免使用冷淡的灰蓝色", "不要让用户头像尺寸过小"],
    },
    "pet-care": {
        "name": "Pet Care", "primary": "#F97316", "secondary": "#22C55E",
        "background": "#FFF7ED", "text": "#431407",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向宠物服务、宠物商店的温馨设计系统",
        "anti_patterns": ["避免使用冷色调", "不要让文字过于严肃正式"],
    },
    "parenting": {
        "name": "Parenting", "primary": "#06B6D4", "secondary": "#F472B6",
        "background": "#ECFEFF", "text": "#164E63",
        "font": "'Nunito', 'Noto Sans SC', system-ui, sans-serif",
        "tone": "活泼",
        "desc": "面向亲子育儿、儿童成长的柔软设计系统",
        "anti_patterns": ["避免使用锐利的角落", "不要让文字字号小于 14px"],
    },
    "music-production": {
        "name": "Music Production", "primary": "#A855F7", "secondary": "#EC4899",
        "background": "#0A0A0A", "text": "#E2E8F0",
        "font": "'Inter', system-ui, sans-serif",
        "tone": "科技",
        "desc": "面向音乐制作、音频编辑的创意设计系统",
        "anti_patterns": ["避免静物感强的灰度配色", "不要让轨道面板的可读性降低"],
    },
}


def apply_template(template_name: str, overrides: Dict[str, Optional[str]]) -> Dict[str, str]:
    """应用模板，允许用户通过 overrides 覆盖模板中的任意字段。"""
    tpl = TEMPLATES.get(template_name, TEMPLATES["enterprise"])
    result = dict(tpl)
    for key, val in overrides.items():
        if val is not None and val != "":
            result[key] = val
    return result


# ═══════════════════════════════════════════════════════════════
# P1-1: 深色主题阴影
# ═══════════════════════════════════════════════════════════════

def elevation_tokens(dark: bool) -> List[Tuple[str, str]]:
    """根据主题返回阴影令牌列表。"""
    color = "255,255,255" if dark else "0,0,0"
    return [
        ("none", "none"),
        ("sm", f'"0px 1px 2px 0px rgba({color},0.05)"'),
        ("md", f'"0px 2px 4px 0px rgba({color},0.08), 0px 1px 2px -1px rgba({color},0.06)"'),
        ("lg", f'"0px 4px 8px 0px rgba({color},0.08), 0px 2px 4px -2px rgba({color},0.06)"'),
        ("xl", f'"0px 8px 16px 0px rgba({color},0.08), 0px 4px 8px -4px rgba({color},0.06)"'),
        ("2xl", f'"0px 16px 24px 0px rgba({color},0.10), 0px 8px 16px -8px rgba({color},0.06)"'),
    ]


# ═══════════════════════════════════════════════════════════════
# 调性映射
# ═══════════════════════════════════════════════════════════════

TONE_MAP = {
    "专业": {"error": "#D93025", "success": "#188038", "warning": "#F9AB00", "info": "#1967D2"},
    "活泼": {"error": "#E52521", "success": "#00C853", "warning": "#FFD600", "info": "#2979FF"},
    "极简": {"error": "#B3261E", "success": "#1E8E3E", "warning": "#F2A900", "info": "#1565C0"},
    "科技": {"error": "#FF1744", "success": "#00E676", "warning": "#FFEA00", "info": "#00B0FF"},
    "优雅": {"error": "#C62828", "success": "#2E7D32", "warning": "#F57F17", "info": "#1565C0"},
}

TONE_DESC = {
    "专业": "清晰、精确、可信赖。我们通过克制的视觉语言传递专业度。",
    "活泼": "明快、有趣、有感染力。我们通过大胆的色彩和动态感传递活力。",
    "极简": "简洁、聚焦、去干扰。我们通过留白和克制传递清晰感。",
    "科技": "前卫、精准、有力量。我们通过高对比和几何元素传递科技感。",
    "优雅": "精致、从容、有质感。我们通过细腻的细节和温暖的色调传递优雅。",
}


# ═══════════════════════════════════════════════════════════════
# YAML 前置元数据生成
# ═══════════════════════════════════════════════════════════════

def build_color_theme(args) -> ColorTheme:
    """根据参数构建完整的颜色主题（含所有派生色）。"""
    primary = validate_color(args.primary, "primary")
    secondary = validate_color(args.secondary, "secondary")
    background = validate_color(args.background, "background")
    text_color = validate_color(args.text, "text")

    # 主题判断：显式 --theme dark 优先；否则按背景亮度
    is_dark = False
    if args.theme == "dark":
        is_dark = True
    elif args.theme == "light":
        is_dark = False
    else:
        is_dark = is_dark_bg(background)

    if is_dark:
        surface_color = lighten_color(background, 0.05)
        surface_hover = lighten_color(background, 0.10)
        text_secondary = lighten_color(background, 0.55)
        text_disabled = lighten_color(background, 0.38)
        border_color = lighten_color(background, 0.20)
        divider_color = lighten_color(background, 0.15)
    else:
        surface_color = darken_color(background, 0.02)
        surface_hover = darken_color(background, 0.05)
        text_secondary = darken_color(background, 0.55)
        # 修复：浅色主题下 disabled 必须比 secondary 更浅/更淡
        text_disabled = darken_color(background, 0.30)
        border_color = darken_color(background, 0.15)
        divider_color = darken_color(background, 0.12)

    return ColorTheme(
        primary=primary,
        secondary=secondary,
        background=background,
        text=text_color,
        is_dark=is_dark,
        surface=surface_color,
        surface_hover=surface_hover,
        text_secondary=text_secondary,
        text_disabled=text_disabled,
        border=border_color,
        divider=divider_color,
    )


def generate_yaml_frontmatter(args, theme: Optional[ColorTheme] = None) -> Tuple[str, ColorTheme]:
    """生成 YAML 前置元数据与 ColorTheme 对象。"""
    if theme is None:
        theme = build_color_theme(args)

    tone = args.tone if args.tone in VALID_TONES else "专业"
    tone_colors = TONE_MAP[tone]
    name_esc = escape_yaml(args.name)
    desc_esc = escape_yaml(args.description) if args.description else ""
    version_esc = escape_yaml(args.version or "alpha")
    font = args.font or DEFAULT_FONT

    lines = ["---"]
    lines.append(f'version: "{version_esc}"')
    lines.append(f'name: "{name_esc}"')
    if desc_esc:
        lines.append(f'description: "{desc_esc}"')

    lines.append("")
    lines.append("# ===== Colors =====")
    lines.append("colors:")
    for k, v in [
        ("primary", theme.primary),
        ("primary-hover", darken_color(theme.primary)),
        ("primary-active", darken_color(theme.primary, 0.25)),
        ("primary-light", lighten_color(theme.primary)),
        ("secondary", theme.secondary),
        ("secondary-hover", darken_color(theme.secondary)),
        ("background", theme.background),
        ("surface", theme.surface),
        ("surface-hover", theme.surface_hover),
        ("text-primary", theme.text),
        ("text-secondary", theme.text_secondary),
        ("text-disabled", theme.text_disabled),
        ("border", theme.border),
        ("divider", theme.divider),
        ("error", tone_colors["error"]),
        ("success", tone_colors["success"]),
        ("warning", tone_colors["warning"]),
        ("info", tone_colors["info"]),
        ("white", "#FFFFFF"),
        ("black", "#000000"),
    ]:
        lines.append(f'  {k}: "{v}"')

    if args.accent_colors:
        for i, c in enumerate(args.accent_colors):
            lines.append(f'  accent-{i + 1}: "{c}"')

    # 字体
    mono_font = DEFAULT_MONO_FONT
    if args.font:
        first_font = args.font.split(",")[0].strip().strip("'\"")
        if first_font:
            mono_font = f"'{first_font}-Mono', {DEFAULT_MONO_FONT}"

    lines.append("")
    lines.append("# ===== Typography =====")
    lines.append("typography:")
    for token, size, weight, lh, ls in [
        ("display-1", "64px", "800", "1.1", "-0.03em"),
        ("display-2", "48px", "700", "1.15", "-0.02em"),
        ("heading-1", "36px", "700", "1.2", "-0.02em"),
        ("heading-2", "28px", "600", "1.25", None),
        ("heading-3", "22px", "600", "1.3", None),
        ("subtitle", "18px", "500", "1.4", "0.01em"),
        ("body", "16px", "400", "1.5", None),
        ("body-small", "14px", "400", "1.5", None),
        ("caption", "12px", "400", "1.4", "0.02em"),
        ("button", "14px", "600", "1", "0.02em"),
        ("overline", "11px", "700", "1", "0.08em"),
    ]:
        lines.append(f"  {token}:")
        lines.extend([
            f'    fontFamily: "{font}"',
            f"    fontSize: {size}",
            f"    fontWeight: {weight}",
            f"    lineHeight: {lh}",
        ])
        if ls:
            lines.append(f"    letterSpacing: {ls}")
    lines.append("  code:")
    lines.extend([
        f'    fontFamily: "{mono_font}"',
        "    fontSize: 14px",
        "    fontWeight: 400",
        "    lineHeight: 1.6",
    ])

    # 圆角
    lines.append("")
    lines.append("# ===== Rounded Corners =====")
    lines.append("rounded:")
    for k, v in [("none", "0px"), ("sm", "4px"), ("md", "8px"), ("lg", "12px"),
                 ("xl", "16px"), ("2xl", "24px"), ("full", "9999px")]:
        lines.append(f"  {k}: {v}")

    # 间距
    lines.append("")
    base = getattr(args, "spacing_base", 4) or 4
    base = max(2, min(16, base))
    lines.append("# ===== Spacing =====")
    lines.append("spacing:")
    for k, v in [("0", "0px"), ("xs", f"{base}px"), ("sm", f"{base * 2}px"),
                 ("md", f"{base * 4}px"), ("lg", f"{base * 6}px"),
                 ("xl", f"{base * 8}px"), ("2xl", f"{base * 12}px"),
                 ("3xl", f"{base * 16}px"), ("4xl", f"{base * 24}px")]:
        lines.append(f"  {k}: {v}")

    # 阴影
    lines.append("")
    lines.append("# ===== Elevation =====")
    lines.append("elevation:")
    for k, v in elevation_tokens(theme.is_dark):
        lines.append(f"  {k}: {v}")

    # 组件
    lines.append("")
    lines.append("# ===== Components =====")
    components = """  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 12px 24px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.white}"
  button-primary-disabled:
    backgroundColor: "{colors.text-disabled}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: transparent
    textColor: "{colors.primary}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 12px 24px
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    borderColor: "{colors.border}"
    padding: 10px 12px
  input-focus:
    backgroundColor: "{colors.background}"
    borderColor: "{colors.primary}"
  input-error:
    backgroundColor: "{colors.background}"
    borderColor: "{colors.error}"
  textarea:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    borderColor: "{colors.border}"
    padding: 10px 12px
  select:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    borderColor: "{colors.border}"
    padding: 10px 12px
  checkbox:
    backgroundColor: "{colors.background}"
    borderColor: "{colors.border}"
    rounded: "{rounded.sm}"
    width: 18px
    height: 18px
  checkbox-checked:
    backgroundColor: "{colors.primary}"
    borderColor: "{colors.primary}"
  radio:
    backgroundColor: "{colors.background}"
    borderColor: "{colors.border}"
    rounded: "{rounded.full}"
    width: 18px
    height: 18px
  switch:
    backgroundColor: "{colors.text-disabled}"
    rounded: "{rounded.full}"
    width: 40px
    height: 22px
  switch-active:
    backgroundColor: "{colors.primary}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  card-hover:
    backgroundColor: "{colors.surface-hover}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  badge:
    rounded: "{rounded.full}"
    padding: 2px 8px
    typography: "{typography.caption}"
  avatar:
    backgroundColor: "{colors.primary-light}"
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
    typography: "{typography.body}"
  navbar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    padding: 16px 24px
    typography: "{typography.body}"
  tabs:
    backgroundColor: transparent
    textColor: "{colors.text-secondary}"
    borderBottom: "{colors.border}"
    typography: "{typography.body}"
  tab-active:
    textColor: "{colors.primary}"
    borderBottom: "{colors.primary}"
    typography: "{typography.button}"
  breadcrumbs:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-small}"
  table:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.border}"
    typography: "{typography.body}"
  table-header:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-small}"
  table-row-hover:
    backgroundColor: "{colors.surface-hover}"
  pagination:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-small}"
  tooltip:
    backgroundColor: "{colors.text-primary}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
    padding: 4px 8px
    typography: "{typography.caption}"
  modal:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  modal-overlay:
    backgroundColor: "rgba(0,0,0,0.5)"
  toast:
    backgroundColor: "{colors.text-primary}"
    textColor: "{colors.background}"
    rounded: "{rounded.md}"
    padding: 12px 16px
    typography: "{typography.body-small}"
  toast-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.white}"
  toast-error:
    backgroundColor: "{colors.error}"
    textColor: "{colors.white}"
  dropdown:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.md}"
    typography: "{typography.body-small}"
  progress:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.full}"
    height: 6px
  progress-bar:
    backgroundColor: "{colors.primary}"
    rounded: "{rounded.full}"
  skeleton:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.sm}"
  empty-state:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    padding: "{spacing.3xl} {spacing.md}"
  container:
    maxWidth: 1200px
    padding: "0 {spacing.md}"
"""
    lines.extend(components.split("\n"))
    if lines and lines[-1] == "":
        lines.pop()
    lines.append("---")

    return "\n".join(lines), theme


# ═══════════════════════════════════════════════════════════════
# Markdown 正文生成
# ═══════════════════════════════════════════════════════════════

def generate_markdown_body(args, theme: ColorTheme) -> str:
    tone = args.tone if args.tone in VALID_TONES else "专业"
    font = args.font or DEFAULT_FONT
    primary = theme.primary
    secondary = theme.secondary
    background = theme.background
    text = theme.text
    is_dark = theme.is_dark

    contrast_note = (
        f"注意：这是一个深色主题设计。正文文字采用浅色（{text}），"
        f"确保在深色背景（{background}）上有充足的对比度。"
        if is_dark else ""
    )

    shadow_desc = "亮色阴影" if is_dark else "暗色阴影"

    sections = []
    sections.append(f"""## Overview

{args.name} 的设计系统围绕以下核心原则构建：

- **{TONE_DESC[tone]}**
- **一致性**：所有组件共享统一的设计语言，确保用户在不同页面间获得连贯体验
- **可访问性**：色彩对比度不低于 WCAG AA 标准，所有交互元素有明确焦点状态
- **可扩展性**：设计令牌体系支持从单一页面到复杂应用的无缝扩展

{contrast_note}

> 本文件符合 Google Labs design.md v{args.version or "alpha"} 规范，可作为 AI 编码代理的设计参考。
""")

    sections.append(f"""## Colors

色板系统分为语义色和中性色两大类。

### 语义色

- **Primary（{primary}）**：品牌主色，用于主要行动按钮、链接、活动态元素
- **Primary Hover（{darken_color(primary)}）**：Primary 的悬停状态
- **Primary Active（{darken_color(primary, 0.25)}）**：Primary 的按下状态
- **Primary Light（{lighten_color(primary)}）**：Primary 的浅色背景态，用于标签或背景填充
- **Secondary（{secondary}）**：辅助色，用于次要行动按钮、成功状态反馈

### 语义功能色

- **Error（{TONE_MAP[tone]['error']}）**：错误状态、必填校验
- **Success（{TONE_MAP[tone]['success']}）**：成功状态、完成确认
- **Warning（{TONE_MAP[tone]['warning']}）**：警告状态、需要关注的信息
- **Info（{TONE_MAP[tone]['info']}）**：提示信息、引导性内容

### 中性色

背景色（{background}）、表面色（{theme.surface}）、文字色（{text}）、边框色、分割线色构成页面的基础层次结构。

### 使用规则

- **主色使用率**：主色在界面中的占比不超过 15%，避免视觉疲劳
- **对比度要求**：所有文字与背景的对比度不低于 4.5:1（AA 标准），大号文字不低于 3:1
- **色盲友好**：不使用纯红色或纯绿色作为唯一的区分信息手段
""")

    sections.append(f"""## Typography

采用 **{font}** 作为首选字体族，等宽字体用于代码场景。

### 字体层级

| Token | 字号 | 字重 | 行高 | 字间距 | 用途 |
|-------|------|------|------|--------|------|
| display-1 | 64px | 800 | 1.1 | -0.03em | 大屏展示标题 |
| display-2 | 48px | 700 | 1.15 | -0.02em | 页面主标题 |
| heading-1 | 36px | 700 | 1.2 | -0.02em | 区块标题 |
| heading-2 | 28px | 600 | 1.25 | - | 子标题 |
| heading-3 | 22px | 600 | 1.3 | - | 卡片标题 |
| subtitle | 18px | 500 | 1.4 | 0.01em | 副标题说明 |
| body | 16px | 400 | 1.5 | - | 正文 |
| body-small | 14px | 400 | 1.5 | - | 次要正文 |
| caption | 12px | 400 | 1.4 | 0.02em | 辅助说明文字 |
| button | 14px | 600 | 1 | 0.02em | 按钮文字 |
| code | 14px | 400 | 1.6 | - | 行内代码/代码块 |
| overline | 11px | 700 | 1 | 0.08em | 上标标签文字 |

### 使用规则

- **层级约束**：heading-1 到 heading-3 必须按顺序使用，不可跳级
- **行长度**：正文单行不超过 80 字符（约 640px），确保阅读舒适度
- **响应式降级**：移动端 display-1 降级为 40px，heading-1 降级为 28px
""")

    b = getattr(args, "spacing_base", 4) or 4
    sections.append(f"""## Layout & Spacing

### 间距体系

采用 **{b}px 基准网格**，所有间距值均为 {b}px 的倍数：

| Token | 值 | 场景 |
|-------|-----|------|
| xs | {b}px | 图标与文字间距 |
| sm | {b * 2}px | 组件内元素间距 |
| md | {b * 4}px | 组件间距、段落间距 |
| lg | {b * 6}px | 区块间距 |
| xl | {b * 8}px | 大区块间距 |
| 2xl | {b * 12}px | 页面分区间距 |
| 3xl | {b * 16}px | 页面顶部/底部间距 |
| 4xl | {b * 24}px | 超大留白 |

### 布局原则

- **响应式断点**：768px（平板）、1024px（桌面）、1440px（宽屏）
- **内容最大宽度**：1200px，超出时居中留白
- **网格**：12 列网格系统，列间距 24px
""")

    sections.append(f"""## Elevation & Depth

阴影层级通过 Z 轴深度传达元素的层级关系。本设计采用{shadow_desc}阴影体系：

| Token | 阴影值 | 用途 |
|-------|--------|------|
| none | 无阴影 | 平铺内容 |
| sm | 1px 高度 | 卡片默认态 |
| md | 2px 高度 | 下拉菜单 |
| lg | 4px 高度 | 弹窗/对话框 |
| xl | 8px 高度 | 模态框 |
| 2xl | 16px 高度 | 顶部导航/全局通知 |

### 使用规则

- **避免层级堆叠**：同一页面不超过 3 个阴影层级
- **Z-index 范围**：sticky(100) -> dropdown(1000) -> modal(5000) -> toast(10000)
""")

    sections.append("""## Shapes

### 圆角体系

| Token | 值 | 场景 |
|-------|-----|------|
| none | 0px | 表格、列表 |
| sm | 4px | 输入框 |
| md | 8px | 按钮、卡片 |
| lg | 12px | 弹窗、大卡片 |
| xl | 16px | 搜索条 |
| full | 9999px | 徽章、头像、标签 |

### 使用规则

- **统一性**：同类型组件使用一致的圆角值
- **矛盾**：不应在卡片的顶角和底角使用不同的圆角值
""")

    sections.append(f"""## Components

### 按钮（Button）

| 变体 | 背景 | 文字 | 场景 |
|------|------|------|------|
| primary | primary | white | 主要操作 |
| primary-hover | primary-hover | white | 悬停 |
| primary-disabled | text-disabled | white | 不可用 |
| secondary | 透明 | primary | 次要操作 |

规格：高 40px，水平内边距 24px，圆角 8px，字号 14px / 字重 600。

### 输入（Input / Select / Textarea）

规格：高 40px，圆角 4px，内边距 10px 12px。Select 和 Textarea 同规格。

| 状态 | 说明 |
|------|------|
| default | 1px solid {theme.border} 边框 |
| focus | 2px solid primary 边框 |
| error | 2px solid error 边框 + 错误提示文字 |

### 选择控件（Checkbox / Radio / Switch）

- Checkbox、Radio：18x18px，支持 checked / focus / disabled 状态
- Switch：40x22px，默认 text-disabled 灰色，激活后 primary

### 卡片（Card）

sm 级阴影，surface 色背景，16px 圆角，24px 内边距。hover 升至 md 阴影，背景切 surface-hover。

### 导航（Navbar / Tabs / Breadcrumbs）

- **Navbar**：surface 底色，水平内边距 24px
- **Tabs**：下划线式，默认 text-secondary，激活态 primary + 2px 下划线
- **Breadcrumbs**：text-secondary，body-small 字号

### 数据展示（Table / Pagination / Tooltip）

- **Table**：支持 header (surface 底色 + 600 字重)、行 hover (surface-hover)
- **Pagination**：body-small 字号，当前页 primary
- **Tooltip**：text-primary 底色 + 反白文字，4px 8px 内边距

### 反馈（Modal / Toast / Dropdown）

- **Modal**：居中浮层，xl 内边距，半透明遮罩层
- **Toast**：深底反白，success/error 变体用语义色
- **Dropdown**：surface 底色，md 圆角，border 描边

### 信息展示（Badge / Avatar / Progress / Skeleton / Empty State）

- **Badge**：full 圆角，caption 字号
- **Avatar**：primary-light 底色 + primary 文字，full 圆角，40x40px
- **Progress**：surface 底 6px 轨道 + primary 填充条
- **Skeleton**：surface 底色 sm 圆角占位块
- **Empty State**：居中 text-secondary，3xl 垂直内边距

### 布局（Container）

内容区最大宽度 1200px，水平居中，内边距 md (16px)。
""")

    sections.append(f"""## Do's and Don'ts

### Do's

- 使用设计令牌引用而非硬编码值（如 `{{{{colors.primary}}}}` 而非 `\"{primary}\"`）
- 遵循字体层级约束，从 display-1 到 body 按需递减
- 确保所有交互元素有明确的 hover 和 focus 状态
- {"在深色背景上使用白色文字" if is_dark else "在浅色背景上使用深色文字"}
- 对于彩色按钮，hover 状态应比默认加深 15%

### Don'ts

- 不要在一个页面中使用超过 3 种强调色
- {"不要在浅色背景上使用浅色文字" if is_dark else "不要在正文中使用纯黑色（#000000）——使用 text-primary（" + text + "）"}
- 不要直接修改设计令牌的值——如需变更，更新 DESIGN.md 中的定义
- 不要在卡片上叠加阴影再叠加阴影——嵌套元素不应自带入额外的阴影层级
- 不要为文字内容随意指定字号——必须从字体层级中选择
""")
    ap_name = getattr(args, "template", "") or ""
    if ap_name and ap_name in TEMPLATES:
        anti = TEMPLATES[ap_name].get("anti_patterns", [])
        if anti:
            sections[-1] = sections[-1].rstrip() + """

### 行业反模式 — %s

""" % TEMPLATES[ap_name]["name"]
            for i, a in enumerate(anti, 1):
                sections[-1] += "- ❌ %s\n" % a
            sections[-1] += "\n"

    return "\n\n".join(sections)


# ═══════════════════════════════════════════════════════════════
# 主构建
# ═══════════════════════════════════════════════════════════════

def build_design_md(args) -> Tuple[str, ColorTheme]:
    frontmatter, theme = generate_yaml_frontmatter(args)
    body = generate_markdown_body(args, theme)

    pairs = [
        ("正文", "背景", theme.text, theme.background),
        ("正文", "表面色", theme.text, theme.surface),
        ("主色", "白色", theme.primary, "#FFFFFF"),
    ]
    check_contrast_pairs(pairs, args.name)

    generated_note = f"""<!--
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Generator: design-spec Skill (WorkBuddy)
Based on: google-labs-code/design.md specification (v{args.version or "alpha"})
-->

"""
    return frontmatter + "\n\n" + generated_note + body + "\n", theme


# ═══════════════════════════════════════════════════════════════
# P0-4: 原子写入 + P0-5: 路径安全
# ═══════════════════════════════════════════════════════════════

def _is_path_safe(path: str) -> bool:
    """拒绝包含 .. 的路径，防止目录遍历。"""
    parts = Path(path).parts
    return ".." not in parts


def resolve_output_path(path: str) -> str:
    """解析并校验输出路径。"""
    if not path:
        path = "DESIGN.md"
    if not _is_path_safe(path):
        raise ValidationError(f"输出路径包含目录遍历（..）: {path}")
    return str(Path(path).resolve())


def safe_write(filepath: str, content: str):
    output_dir = os.path.dirname(filepath) or "."
    os.makedirs(output_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp", prefix="design_spec_", dir=output_dir, text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ═══════════════════════════════════════════════════════════════
# P1-3: 版本化输出
# ═══════════════════════════════════════════════════════════════

def build_output_path(path: str, with_timestamp: bool) -> str:
    if not with_timestamp:
        return path
    dirname = os.path.dirname(path) or "."
    basename = os.path.basename(path)
    name, ext = os.path.splitext(basename)
    date_suffix = datetime.now().strftime("%Y%m%d")
    return os.path.join(dirname, f"{name}_{date_suffix}{ext}")


# ═══════════════════════════════════════════════════════════════
# P2-1: 色板可视化（SVG）
# ═══════════════════════════════════════════════════════════════

def generate_palette_svg(theme: ColorTheme, name: str, output_path: str, tone: str, accent_colors: Optional[List[str]] = None):
    """生成色板预览 SVG，与 DESIGN.md 同目录输出。主题背景随设计深浅切换。"""
    accent_colors = accent_colors or []
    groups = [
        ("品牌语义色", ["primary", "primary-hover", "primary-active", "primary-light", "secondary", "secondary-hover"]),
        ("中性色", ["background", "surface", "surface-hover", "border", "divider"]),
        ("文字色", ["text-primary", "text-secondary", "text-disabled"]),
        ("语义功能色", ["error", "success", "warning", "info"]),
        ("基准色", ["white", "black"]),
    ]
    if accent_colors:
        groups.append(("强调色", [f"accent-{i + 1}" for i in range(len(accent_colors))]))

    # 将派生色名映射到真实 hex
    color_map = {
        "primary": theme.primary,
        "primary-hover": darken_color(theme.primary),
        "primary-active": darken_color(theme.primary, 0.25),
        "primary-light": lighten_color(theme.primary),
        "secondary": theme.secondary,
        "secondary-hover": darken_color(theme.secondary),
        "background": theme.background,
        "surface": theme.surface,
        "surface-hover": theme.surface_hover,
        "text-primary": theme.text,
        "text-secondary": theme.text_secondary,
        "text-disabled": theme.text_disabled,
        "border": theme.border,
        "divider": theme.divider,
        "error": TONE_MAP.get(tone, TONE_MAP["专业"])["error"],
        "success": TONE_MAP.get(tone, TONE_MAP["专业"])["success"],
        "warning": TONE_MAP.get(tone, TONE_MAP["专业"])["warning"],
        "info": TONE_MAP.get(tone, TONE_MAP["专业"])["info"],
        "white": "#FFFFFF",
        "black": "#000000",
    }
    for i, c in enumerate(accent_colors):
        color_map[f"accent-{i + 1}"] = c

    swatch_size = 80
    swatch_gap = 8
    label_height = 36
    group_gap = 28
    margin = 24
    width = 460

    total_height = margin
    for group_name, tokens in groups:
        rows = (len(tokens) + 2) // 3
        total_height += label_height + rows * (swatch_size + label_height + swatch_gap) + group_gap
    total_height += margin

    svg_bg = "#1e1e1e" if theme.is_dark else "#f8f9fa"
    title_color = "#e0e0e0" if theme.is_dark else "#1a1c1e"
    group_title_color = "#9aa0a6" if theme.is_dark else "#5f6368"
    token_label_color = "#cccccc" if theme.is_dark else "#3c4043"
    hex_color = "#888888" if theme.is_dark else "#5f6368"

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_height}"',
        f'     width="{width}" height="{total_height}"',
        f'     style="background:{svg_bg};font-family:system-ui,sans-serif">',
        f'<text x="{margin}" y="44" fill="{title_color}" font-size="18" font-weight="700">{escape_xml(name)} — 色板预览</text>',
    ]

    y = margin + 44 + 12

    for group_name, tokens in groups:
        svg_parts.append(f'<text x="{margin}" y="{y}" fill="{group_title_color}" font-size="13" font-weight="600">{escape_xml(group_name)}</text>')
        y += label_height

        for i, token in enumerate(tokens):
            col = i % 3
            row = i // 3
            color_val = color_map.get(token, "#CCCCCC")

            x_pos = margin + col * (swatch_size + swatch_gap)
            y_pos = y + row * (swatch_size + label_height + swatch_gap)

            svg_parts.append(
                f'<rect x="{x_pos}" y="{y_pos}" width="{swatch_size}" height="{swatch_size}" '
                f'rx="6" fill="{color_val}" stroke="#333" stroke-width="1"/>'
            )
            svg_parts.append(
                f'<text x="{x_pos + swatch_size / 2}" y="{y_pos + swatch_size + 14}" '
                f'fill="{token_label_color}" font-size="10" text-anchor="middle">{escape_xml(token)}</text>'
            )
            svg_parts.append(
                f'<text x="{x_pos + swatch_size / 2}" y="{y_pos + swatch_size + 26}" '
                f'fill="{hex_color}" font-size="9" text-anchor="middle">{color_val}</text>'
            )

        y += ((len(tokens) + 2) // 3) * (swatch_size + label_height + swatch_gap) + group_gap

    svg_parts.append("</svg>")

    svg_path = output_path.replace(".md", "_palette.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    return svg_path


def escape_xml(value: str) -> str:
    return (value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


# ═══════════════════════════════════════════════════════════════
# P2-3: 多语言字体自动匹配
# ═══════════════════════════════════════════════════════════════

def detect_preferred_font(name: str, description: str, user_font: str) -> str:
    """检测品牌名/描述是否包含中文，自动推荐中文字体。"""
    if user_font:
        return user_font
    text = f"{name} {description}"
    has_cjk = bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
    return DEFAULT_CJK_FONT if has_cjk else DEFAULT_FONT


# ═══════════════════════════════════════════════════════════════
# P2-2: 迭代修改（重新生成以保持派生色一致）
# ═══════════════════════════════════════════════════════════════

def parse_yaml_frontmatter(content: str) -> Dict[str, str]:
    """轻量解析 DESIGN.md 的 YAML 前置元数据，提取可修改字段。"""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    yaml_text = match.group(1)
    result = {}

    # name / description / version
    for key in ("name", "description", "version"):
        m = re.search(rf'^{key}:\s*"(.*?)"$', yaml_text, re.MULTILINE)
        if m:
            result[key] = m.group(1)

    # colors
    colors_section = re.search(r'^colors:\n(.*?)(?=^\w|\Z)', yaml_text, re.MULTILINE | re.DOTALL)
    if colors_section:
        for m in re.finditer(r'^\s+([\w-]+):\s*"([^"]*)"', colors_section.group(1), re.MULTILINE):
            key, val = m.group(1), m.group(2)
            if key in ("primary", "secondary", "background"):
                result[key] = val
            elif key == "text-primary":
                result["text"] = val

    # font / tone（从 Markdown 正文推断 tone）
    font_m = re.search(r'fontFamily:\s*"(.*?)"', yaml_text)
    if font_m:
        result["font"] = font_m.group(1)

    return result


def modify_design_md(filepath: str, overwrites: Dict[str, str], output_path: str, spacing_base: int = 4):
    """读取已有 DESIGN.md，解析原参数，应用覆盖后重新生成，确保派生色一致。"""
    with open(filepath, "r", encoding="utf-8") as f:
        original_content = f.read()

    base = parse_yaml_frontmatter(original_content)
    if not base:
        raise ValidationError(f"无法解析 {filepath} 的 YAML 前置元数据")

    # 应用覆盖
    for key, value in overwrites.items():
        if key in ("primary", "secondary", "background", "text", "name", "font", "tone"):
            base[key] = value

    # 构建临时参数对象
    class Args:
        pass

    args = Args()
    args.name = base.get("name", "Modified")
    args.description = base.get("description", "")
    args.version = base.get("version", "alpha")
    args.primary = base.get("primary", "")
    args.secondary = base.get("secondary", "")
    args.background = base.get("background", "")
    args.text = base.get("text", "")
    args.font = base.get("font", "")
    args.tone = base.get("tone", "专业")
    args.theme = "auto"
    args.accent_colors = []
    args.spacing_base = spacing_base

    content, _theme = build_design_md(args)
    safe_write(output_path, content)

    print(f"迭代修改完成：{output_path}")
    print(f"   修改的字段：{', '.join(overwrites.keys())}")


# ═══════════════════════════════════════════════════════════════
# M1: 代码导出引擎（优先使用 @google/design.md 官方 CLI）
# ═══════════════════════════════════════════════════════════════

def _find_npx() -> str:
    """自动发现 npx 路径，优先系统 PATH，回退 WorkBuddy 托管路径。"""
    import shutil
    npx = shutil.which("npx")
    if npx:
        return npx
    home = os.path.expanduser("~")
    for version in ("22.22.2", "24.16.0"):
        wb_npx = os.path.join(home, f".workbuddy/binaries/node/versions/{version}/bin/npx")
        if os.path.exists(wb_npx):
            return wb_npx
    return "npx"


def handle_export(design_md_path: str, export_format: str):
    """通过官方 @google/design.md CLI 导出令牌。"""
    fmt_map = {
        "tailwind": "json-tailwind",
        "css": "css-tailwind",
        "dtcg": "dtcg",
    }
    cli_format = fmt_map.get(export_format, export_format)
    base = os.path.splitext(design_md_path)[0]
    output_map = {
        "tailwind": base + "_tailwind.theme.json",
        "css": base + "_tokens.css",
        "dtcg": base + "_tokens.json",
    }
    output_path = output_map[export_format]

    npx_path = _find_npx()
    env = os.environ.copy()
    home = os.path.expanduser("~")
    wb_node_modules = os.path.join(home, ".workbuddy/binaries/node/workspace/node_modules")
    if os.path.isdir(wb_node_modules):
        env["NODE_PATH"] = wb_node_modules
    cmd = [
        npx_path,
        "@google/design.md", "export",
        "--format", cli_format,
        design_md_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        if result.returncode == 0:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            print(f"   {export_format} export: {output_path} (via @google/design.md)")
        else:
            print(f"   [WARN] CLI export failed, using fallback: {result.stderr[:200]}")
            _fallback_export(design_md_path, export_format, output_path)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"   [WARN] CLI not available ({e}), using fallback")
        _fallback_export(design_md_path, export_format, output_path)


def _fallback_export(design_md_path: str, export_format: str, output_path: str):
    """官方 CLI 不可用时的 fallback 导出。"""
    tokens = _extract_tokens_fallback(design_md_path)
    if export_format == "tailwind":
        config = {"theme": {"extend": {}}}
        if "colors" in tokens:
            tw = {}
            for k, v in tokens["colors"].items():
                if k not in ("white", "black"):
                    tw[k] = v
            config["theme"]["extend"]["colors"] = tw
        if "rounded" in tokens:
            config["theme"]["extend"]["borderRadius"] = tokens["rounded"]
        if "spacing" in tokens:
            config["theme"]["extend"]["spacing"] = tokens["spacing"]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    elif export_format == "css":
        lines = ["@theme {", "  /* Generated by design-spec Skill */"]
        if "colors" in tokens:
            for k, v in tokens["colors"].items():
                lines.append(f"  --color-{k}: {v};")
        if "rounded" in tokens:
            for k, v in tokens["rounded"].items():
                lines.append(f"  --rounded-{k}: {v};")
        if "spacing" in tokens:
            for k, v in tokens["spacing"].items():
                lines.append(f"  --spacing-{k}: {v};")
        lines.append("}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    elif export_format == "dtcg":
        dtcg = {}
        if "colors" in tokens:
            c = {}
            for k, v in tokens["colors"].items():
                c[k] = {"$value": v, "$type": "color"}
            if c:
                dtcg["color"] = c
        if "rounded" in tokens:
            r = {}
            for k, v in tokens["rounded"].items():
                r[k] = {"$value": v, "$type": "dimension"}
            if r:
                dtcg["borderRadius"] = r
        if "spacing" in tokens:
            s = {}
            for k, v in tokens["spacing"].items():
                s[k] = {"$value": v if isinstance(v, str) else f"{v}px", "$type": "dimension"}
            if s:
                dtcg["spacing"] = s
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dtcg, f, indent=2, ensure_ascii=False)
    print(f"   {export_format} export: {output_path} (fallback)")


def _extract_tokens_fallback(filepath: str) -> Dict[str, Dict[str, str]]:
    """从 DESIGN.md 中提取 YAML 令牌（fallback 用）。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    yaml_text = match.group(1)
    tokens: Dict[str, Dict[str, str]] = {}
    colors_section = re.search(r'^colors:\n(.*?)(?=^\w|\Z)', yaml_text, re.MULTILINE | re.DOTALL)
    if colors_section:
        colors = {}
        for m in re.finditer(r'^\s+([\w-]+):\s*"([^"]*)"', colors_section.group(1), re.MULTILINE):
            colors[m.group(1)] = m.group(2)
        tokens["colors"] = colors
    for section in ("rounded", "spacing"):
        sec_m = re.search(rf'^{section}:\n(.*?)(?=^\w|\Z)', yaml_text, re.MULTILINE | re.DOTALL)
        if sec_m:
            values = {}
            for m in re.finditer(r'^\s+([\w-]+):\s*"?([^"\n]+)"?$', sec_m.group(1), re.MULTILINE):
                values[m.group(1)] = m.group(2).strip().strip('"')
            tokens[section] = values
    return tokens


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

def run_lint(filepath: str) -> int:
    """调用官方 @google/design.md lint CLI 校验 DESIGN.md。"""
    npx_path = _find_npx()
    cmd = [npx_path, "@google/design.md", "lint", "--format", "text", filepath]
    try:
        result = subprocess.run(cmd, capture_output=False, timeout=30)
        return result.returncode
    except FileNotFoundError:
        print("错误：@google/design.md CLI 未安装，无法执行 lint")
        print("  安装方式：npm install -g @google/design.md 或使用 npx")
        return 1
    except subprocess.TimeoutExpired:
        print("错误：lint 超时（30s）")
        return 1


def run_diff(file1: str, file2: str) -> int:
    """调用官方 @google/design.md diff CLI 比较两个 DESIGN.md 的差异。"""
    npx_path = _find_npx()
    cmd = [npx_path, "@google/design.md", "diff", file1, file2]
    try:
        result = subprocess.run(cmd, capture_output=False, timeout=30)
        return result.returncode
    except FileNotFoundError:
        print("错误：@google/design.md CLI 未安装，无法执行 diff")
        print("  安装方式：npm install -g @google/design.md 或使用 npx")
        return 1
    except subprocess.TimeoutExpired:
        print("错误：diff 超时（30s）")
        return 1


def run_self_check():
    """检查所有依赖是否就绪。"""
    import shutil

    checks = []
    checks.append(("Python 3.8+", sys.version_info >= (3, 8)))

    for pkg in ("coloraide", "PIL", "colorthief"):
        try:
            __import__(pkg.replace("PIL", "PIL"))
            checks.append((pkg, True))
        except ImportError:
            checks.append((pkg, False))

    checks.append(("designlang CLI (optional, upstream for URL extraction)", bool(shutil.which("npx"))))

    try:
        result = subprocess.run([_find_npx(), "@google/design.md", "--version"],
                               capture_output=True, text=True, timeout=15)
        md_cli = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        md_cli = False
    checks.append(("@google/design.md CLI (optional, for --export)", md_cli))

    checks.append(("node/npm (optional)", bool(shutil.which("node"))))

    print("design-spec Skill 环境检查")
    print("=" * 40)
    all_ok = True
    for name, ok in checks:
        label = "OK" if ok else "MISSING"
        print(f"  [{label:7s}] {name}")
        if not ok and "optional" not in name:
            all_ok = False

    print()
    if all_ok:
        print("All core dependencies ready.")
    else:
        print("Some core dependencies are missing. Run:")
        print("  pip install coloraide pillow colorthief")

    print()
    print("Optional tools:")
    print("  npx @designlang/cli (for live URL extraction, then --import)")
    print("  npx @google/design.md lint/export (for --export)")
    print("=" * 40)


# ═══════════════════════════════════════════════════════════════
# CLI 与主流程
# ═══════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate DESIGN.md — Hardened Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 从零开始
  %(prog)s --name "MyBrand" --description "SaaS platform" --primary "#1A73E8" --tone "专业"

  # 使用行业模板
  %(prog)s --name "MyShop" --template ecommerce
  %(prog)s --name "MyBank" --template finance --background "#0D1117"

  # 深色主题
  %(prog)s --name "App" --theme dark --background "#1A1C1E" --text "#E8EAED"

  # 版本化输出
  %(prog)s --name "App" --timestamp

  # 代码导出
  %(prog)s --name "App" --export tailwind
  %(prog)s --name "App" --export css --export dtcg

  # 迭代修改
  %(prog)s --modify DESIGN.md --set "primary=#FF6600" --set "tone=活泼"
        """
    )
    parser.add_argument("--name", default="", help="设计系统/品牌名称")
    parser.add_argument("--description", default="", help="品牌或产品描述")
    parser.add_argument("--template", default="", choices=VALID_TEMPLATES,
                        help="行业模板预设")
    parser.add_argument("--theme", default="auto", choices=["light", "dark", "auto"],
                        help="主题模式（auto=根据背景色自动判断）")
    parser.add_argument("--primary", default="", help="主色 (CSS 颜色格式)")
    parser.add_argument("--secondary", default="", help="辅助色 (CSS 颜色格式)")
    parser.add_argument("--background", default="", help="背景色 (CSS 颜色格式)")
    parser.add_argument("--text", default="", help="文字色 (CSS 颜色格式，空=自动匹配)")
    parser.add_argument("--font", default="", help="字体族")
    parser.add_argument("--tone", default="", choices=VALID_TONES, help="设计调性")
    parser.add_argument("--version", default="alpha", help="DESIGN.md 规范版本")
    parser.add_argument("--output", default=None,
                        help="输出文件路径（默认：生成模式为 DESIGN.md；--modify 模式默认覆盖被修改的文件）")
    parser.add_argument("--accent-colors", nargs="*", help="额外强调色列表")
    parser.add_argument("--spacing-base", type=int, default=4,
                        help="间距网格基准像素（默认 4px，可选 8px 等）")
    parser.add_argument("--timestamp", action="store_true",
                        help="在输出文件名中加入时间戳防覆盖")
    parser.add_argument("--visualize", action="store_true",
                        help="同时生成色板预览 SVG")
    parser.add_argument("--export", action="append", default=[],
                        choices=["tailwind", "css", "dtcg"],
                        help="导出工程文件格式（可重复使用）")
    parser.add_argument("--modify", default="",
                        help="读取已存在的 DESIGN.md 文件进行迭代修改")
    parser.add_argument("--set", action="append", default=[],
                        help="修改字段（格式 key=value，可重复使用）")
    parser.add_argument("--analyze", default="",
                        help="分析截图并提取设计令牌（传图片路径）")
    parser.add_argument("--import", dest="import_file", default="",
                        help="导入外部工具（如 designlang）产出的 DESIGN.md，重新对齐官方规范与颜色")
    parser.add_argument("--check", action="store_true",
                        help="检查环境依赖是否就绪")

    parser.add_argument("--lint", default="",
                        help="校验 DESIGN.md 文件，输出 errors/warnings/info")

    parser.add_argument("--diff", nargs=2, default=None,
                        help="比较两个 DESIGN.md 文件的 token 级差异")

    parser.add_argument("--audit", nargs=2, default=None, metavar=("DESIGN.md", "SRC_DIR"),
                        help="审计源码目录中的颜色字面量是否偏离 DESIGN.md 规范（参考 no7z/design-pact）")

    parser.add_argument("--import-local", default="", metavar="PROJECT_DIR",
                        help="从本地项目目录提取设计令牌，自动推导 DESIGN.md 草稿（扫描 CSS 变量、tailwind.config、颜色使用模式）")

    parser.add_argument("--master", default="", metavar="DESIGN.md",
                        help="Master DESIGN.md 路径（作为全局规范的基础，配合 --page 使用）")

    parser.add_argument("--page", default="", metavar="PAGE_NAME",
                        help="页面名称（与 --master 配合：加载 Master 全局规范后应用页面级别的颜色覆盖）")
    return parser


def _insert_suffix(path: str, suffix: str) -> str:
    p = Path(path)
    return str(p.with_name(f"{p.stem}{suffix}{p.suffix}"))


# 扩展的源文件扩展名（审计时扫描的文件类型）
_AUDIT_EXTS = {".css", ".html", ".jsx", ".tsx", ".vue", ".svelte",
               ".scss", ".less", ".styl", ".js", ".ts", ".py",
               ".json", ".yaml", ".yml", ".md", ".xml", ".svg", ".astro"}
_AUDIT_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build",
                    ".next", ".nuxt", ".workbuddy", ".venv", "venv",
                    ".pytest_cache", ".coverage", "htmlcov"}
# 已知第三方库/框架的常见颜色字面量，审计时忽略
_AUDIT_IGNORE_COLORS = {
    "#000000", "#ffffff", "#000", "#fff",
    "#ff0000", "#00ff00", "#0000ff",
    "#f00", "#0f0", "#00f",
    "#ff0", "#f0f", "#0ff",
    "#ffff00", "#ff00ff", "#00ffff",
}


def _collect_design_md_colors(design_path: str) -> tuple[set[str], set[str]]:
    """解析 DESIGN.md 的 colors 块，返回（所有颜色值集合, 颜色键集合）。"""
    try:
        text = Path(design_path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"错误：无法读取 DESIGN.md — {e}")
        return set(), set()
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        print(f"错误：{design_path} 没有 YAML frontmatter")
        return set(), set()
    fm = m.group(1)
    colors_block = re.search(r'^colors:\n(.*?)(?=^\w|\Z)', fm, re.MULTILINE | re.DOTALL)
    if not colors_block:
        print(f"错误：{design_path} 的 colors 块未找到")
        return set(), set()
    allowed = set()
    keys = set()
    for line in colors_block.group(1).splitlines():
        mm = re.match(r'^\s+([\w-]+):\s*"([^"]+)"', line)
        if mm:
            keys.add(mm.group(1))
            try:
                allowed.add(normalize_to_hex(mm.group(2)))
            except ValueError:
                pass
    return allowed, keys


_COLOR_RE = re.compile(
    r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})'
    r'|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*[\d.]+)?\s*\)'
    r'|hsla?\(\s*[\d.]+\s*,\s*[\d.]+%\s*,\s*[\d.]+%(?:\s*,\s*[\d.]+)?\s*\)'
)


def _extract_colors_from_text(text: str) -> list[str]:
    """从文本中提取所有 CSS 颜色字面量并归一化为 6 位 hex。"""
    found = set()
    for m in _COLOR_RE.finditer(text):
        raw = m.group(0).strip()
        if raw.lower() in _AUDIT_IGNORE_COLORS:
            continue
        try:
            found.add(normalize_to_hex(raw))
        except ValueError:
            found.add(raw.lower())
    return sorted(found)


def _run_import_local(project_dir: str, output: str) -> int:
    """扫描本地项目目录，自动推导 DESIGN.md 草稿。

    从 CSS 变量、tailwind.config、颜色使用频率推断设计令牌。
    参考：no7z/design-pact 的 import 命令 / Easy-Hexford local mode。
    """
    src = Path(project_dir).resolve()
    if not src.is_dir():
        print(f"错误：项目目录不存在 — {project_dir}")
        return 1

    print(f"🔍 扫描本地项目: {src}")

    # ── 收集颜色使用频率 ──
    color_freq: dict[str, int] = {}  # hex -> count
    css_vars: dict[str, str] = {}     # --var-name -> value
    fonts_found: set[str] = set()
    tailwind_config = None

    for fpath in src.rglob("*"):
        if any(part.startswith(".") for part in fpath.parts):
            continue
        if any(part in _AUDIT_SKIP_DIRS for part in fpath.parts):
            continue
        if not fpath.is_file():
            continue

        suffix = fpath.suffix.lower()
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        # CSS 变量提取
        if suffix in {".css", ".scss", ".less", ".styl"}:
            for m in re.finditer(r'--([\w-]+)\s*:\s*([^;]+?)\s*(?:!important)?\s*;', text):
                name, val = m.group(1).strip(), m.group(2).strip()
                if val.startswith("#") or val.startswith("rgb") or val.startswith("hsl"):
                    css_vars[f"--{name}"] = val
                # 也提取 font-family 变量
                if "font" in name.lower():
                    css_vars[f"--{name}"] = val

        # Tailwind 配置检测
        if fpath.name in ("tailwind.config.js", "tailwind.config.ts",
                          "tailwind.config.mjs", "tailwind.config.cjs"):
            for m in re.finditer(r"colors\s*:\s*\{([^}]+)\}", text, re.DOTALL):
                colors_block = m.group(1)
                for cm in re.finditer(r"([\w-]+)\s*:\s*['\"]?(#[0-9a-fA-F]+)", colors_block):
                    css_vars[f"--tw-{cm.group(1)}"] = cm.group(2)
                tailwind_config = "tailwind"

        # 颜色频率统计
        for raw in _COLOR_RE.finditer(text):
            col = raw.group(0).strip()
            try:
                hexc = normalize_to_hex(col)
                hexc_lower = hexc.lower()
                if hexc_lower not in _AUDIT_IGNORE_COLORS:
                    color_freq[hexc_lower] = color_freq.get(hexc_lower, 0) + 1
            except ValueError:
                pass

        # 字体检测
        if suffix in {".css", ".scss", ".less", ".html", ".jsx", ".tsx", ".vue"}:
            for m in re.finditer(r'font-family\s*:\s*["\']?([^;"\'}{]+)["\']?', text):
                for fam in m.group(1).split(","):
                    fam = fam.strip().strip("'\"").strip()
                    if fam and fam.lower() not in ("inherit", "initial", "unset", "serif", "sans-serif", "monospace"):
                        fonts_found.add(fam)

    # ── 推断主色 ──
    # 频率最高的颜色 > --color-primary 的值 > --primary 的值
    inferred_primary = ""
    inferred_secondary = ""
    inferred_bg = ""
    inferred_text = ""
    inferred_font = ""

    # 优先从 CSS 变量名推断
    for var_name, var_val in css_vars.items():
        vn = var_name.lower()
        try:
            hexv = normalize_to_hex(var_val)
        except ValueError:
            continue
        if any(k in vn for k in ("primary", "brand", "main")):
            inferred_primary = hexv
        elif any(k in vn for k in ("secondary", "accent")):
            inferred_secondary = hexv
        elif any(k in vn for k in ("bg", "background", "surface")):
            inferred_bg = hexv
        elif any(k in vn for k in ("text", "fg", "foreground")):
            inferred_text = hexv

    # 从频率推断（取 top-3 作为候补）
    sorted_colors = sorted(color_freq.items(), key=lambda x: -x[1])
    if sorted_colors and not inferred_primary:
        inferred_primary = sorted_colors[0][0]
    if len(sorted_colors) > 1 and not inferred_secondary:
        inferred_secondary = sorted_colors[1][0]
    if len(sorted_colors) > 2 and not inferred_bg:
        # 取最高频的浅色作为背景
        for c, _ in sorted_colors:
            if not is_dark_bg(c):
                inferred_bg = c
                break
    if not inferred_bg:
        inferred_bg = "#FFFFFF"

    # 字体推断
    if fonts_found:
        inferred_font = ", ".join(sorted(fonts_found, key=lambda x: -len(x))[:3])

    # ── 生成 DESIGN.md ──
    # 用自动推导的参数调用主生成逻辑
    import argparse
    import types

    local_args = types.SimpleNamespace(
        name=src.name or "Imported Project",
        description=f"从 {src.name} 自动推导的设计规范",
        template="",
        theme="auto",
        primary=inferred_primary,
        secondary=inferred_secondary,
        background=inferred_bg,
        text=inferred_text or "",
        font=inferred_font,
        tone="",
        version="alpha",
        output=output or f"{src.name}_DESIGN.md",
        accent_colors=[c for c, _ in sorted_colors[3:8]],
        spacing_base=4,
        timestamp=False,
        visualize=False,
        export=[],
    )

    print(f"  主色: {inferred_primary or '未推断'}")
    print(f"  辅助色: {inferred_secondary or '未推断'}")
    print(f"  背景色: {inferred_bg}")
    print(f"  字体: {inferred_font or '未推断'}")
    print(f"  置信度: 主色={'HIGH' if inferred_primary else 'N/A'}, "
          f"辅助色={'MEDIUM' if inferred_secondary else 'N/A'}, "
          f"背景色={'HIGH' if inferred_bg else 'N/A'}")
    print(f"  扫描到 CSS 变量: {len(css_vars)} 个, 颜色样本: {len(color_freq)} 个, 字体: {len(fonts_found)} 个")

    try:
        frontmatter, theme = generate_yaml_frontmatter(local_args)
    except ValidationError as e:
        print(f"错误：推导失败 — {e}")
        return 1

    body = generate_markdown_body(local_args, theme)
    content = frontmatter + "\n" + body
    safe_write(local_args.output, content)
    print(f"\n✅ 已生成: {local_args.output}")
    print(f"📝 提示：请检查自动推导的颜色（主色={inferred_primary}），"
          f"可运行 --modify 或重新生成时指定 --primary 修正")
    return 0


def run_audit(design_path: str, source_dir: str) -> int:
    """审计项目源码中的颜色是否偏离 DESIGN.md 规范。

    返回违规颜色数量作为退出码。
    参考：no7z/design-pact 的 check 命令设计思路。
    """
    allowed, keys = _collect_design_md_colors(design_path)
    if not allowed:
        print("  无法提取 DESIGN.md 的颜色令牌，跳过审计")
        return 0

    print(f"📋 DESIGN.md 颜色令牌: {len(allowed)} 个 ({', '.join(sorted(keys)[:8])}{'...' if len(keys) > 8 else ''})")

    violations = []  # (file, line_num, color, context)
    scanned_files = 0

    src = Path(source_dir).resolve()
    design_path_resolved = Path(design_path).resolve()
    if not src.is_dir():
        print(f"错误：源码目录不存在 — {source_dir}")
        return 1

    for fpath in src.rglob("*"):
        # 跳过忽略目录和隐藏目录
        if any(part.startswith(".") and part != "." for part in fpath.parts):
            continue
        if any(part in _AUDIT_SKIP_DIRS for part in fpath.parts):
            continue
        # 跳过 DESIGN.md 文件本身
        if fpath.resolve() == design_path_resolved:
            continue
        if fpath.is_file() and fpath.suffix.lower() in _AUDIT_EXTS:
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            colors_in_file = _extract_colors_from_text(text)
            if not colors_in_file:
                continue
            scanned_files += 1
            for color in colors_in_file:
                if color not in allowed and color not in _AUDIT_IGNORE_COLORS:
                    # 找具体行号
                    rel_path = str(fpath.relative_to(src))
                    for lineno, line in enumerate(text.splitlines(), 1):
                        if color.rstrip(")") in line or color in line or \
                           (color.startswith("#") and color[:7] in line):
                            violations.append((rel_path, lineno, color, line.strip()[:80]))
                            break
                    else:
                        violations.append((rel_path, 0, color, ""))

    # 输出报告
    print(f"🔍 扫描了 {scanned_files} 个源文件")
    if not violations:
        print("✅ 全部颜色字面量均符合 DESIGN.md 规范")
        return 0

    prefix = str(src)
    print(f"⚠️  发现 {len(violations)} 个颜色偏离:\n")
    for fpath, lineno, color, context in violations:
        loc = f"{fpath}:{lineno}" if lineno else fpath
        ctx = f"  // {context}" if context else ""
        print(f"  📄 {loc}{ctx}")
        print(f"    违规颜色: {color}")
        print(f"    预期范围: {', '.join(sorted(allowed)[:5])}{'...' if len(allowed) > 5 else ''}")
        print()

    return len(violations)


def _run_import(import_path: str, output: str) -> int:
    """导入外部工具（如 designlang）产出的 DESIGN.md，重新对齐官方规范。

    仅对 colors 块做颜色归一化（委托 coloraide），其余内容（typography、
    组件、Markdown 正文）原样保留，确保无损。
    """
    if not os.path.exists(import_path):
        print(f"错误：导入文件不存在 — {import_path}")
        return 1
    try:
        text = Path(import_path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"错误：无法读取导入文件 — {e}")
        return 1

    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if m:
        fm = m.group(1)
        body = text[m.end():]
        colors_block = re.search(r'^colors:\n(.*?)(?=^\w|\Z)', fm, re.MULTILINE | re.DOTALL)
        if colors_block:
            new_lines = []
            for line in colors_block.group(1).splitlines():
                mm = re.match(r'^(\s+)([\w-]+):\s*"?([^"\n]*)"?\s*$', line)
                if mm:
                    indent, key, val = mm.group(1), mm.group(2), mm.group(3)
                    if val:
                        try:
                            normed = normalize_to_hex(val)
                            # 置信度评分（参考 DesignTokenX 的 confidence 标注）：
                            # 导入的原始颜色 = HIGH，派生/推断色 = MEDIUM
                            confidence = "HIGH"
                            if any(sfx in key for sfx in ("-hover", "-active", "-light", "-dark", "disabled", "secondary", "border", "divider")):
                                confidence = "MEDIUM"
                            new_lines.append(f'{indent}{key}: "{normed}"  # confidence: {confidence}')
                            continue
                        except ValueError:
                            WARNINGS.add(f"[import] 颜色 {key}={val} 无法归一化，已保留原值")
                    new_lines.append(line)
                else:
                    new_lines.append(line)
            new_block = "\n".join(new_lines) + "\n"
            new_fm = fm[:colors_block.start()] + "colors:\n" + new_block + fm[colors_block.end():]
        else:
            new_fm = fm
        content = "---\n" + new_fm.rstrip() + "\n---\n" + body
    else:
        try:
            data = json.loads(text)
        except Exception:
            print("错误：导入文件既不是 DESIGN.md 也不是 JSON 令牌")
            return 1
        colors = (data.get("colors") or {}) if isinstance(data, dict) else {}
        if not isinstance(colors, dict):
            print("错误：JSON 中未找到 colors 映射")
            return 1
        norm = {}
        for k, v in colors.items():
            if isinstance(v, str):
                try:
                    norm[k] = normalize_to_hex(v)
                except ValueError:
                    norm[k] = v
                    WARNINGS.add(f"[import] 颜色 {k}={v} 无法归一化，已保留原值")
            else:
                norm[k] = v
        content = "---\nversion: \"alpha\"\ncolors:\n" + "".join(
            f'  {k}: "{v}"\n' for k, v in norm.items()
        ) + "---\n\n## Overview\n\nDesign tokens imported and realigned by design-spec.\n"

    out = output or _insert_suffix(import_path, "_realigned")
    safe_write(out, content)
    print(f"导入并重新对齐完成：{out}")
    print(f"  源文件：{import_path}")
    if WARNINGS:
        print("  注意：")
        for w in WARNINGS:
            print(f"   - {w}")
    return 0


def _run_analyze_screenshot(image_path: str, output: str) -> int:
    if not os.path.exists(image_path):
        print(f"错误：截图文件不存在 — {image_path}")
        return 1
    try:
        subprocess.run(
            [sys.executable, ANALYSIS_SCRIPT, image_path, "--output", output],
            check=True, timeout=120,
        )
        return 0
    except subprocess.TimeoutExpired:
        print("错误：截图分析超时（120s）")
        return 1
    except subprocess.CalledProcessError as e:
        print(f"错误：截图分析失败（退出码 {e.returncode}）")
        return 1


def _parse_overwrites(set_args: List[str]) -> Dict[str, str]:
    overwrites: Dict[str, str] = {}
    for s in set_args:
        if "=" not in s:
            WARNINGS.add(f"跳过格式错误的 --set 参数：{s}")
            continue
        k, v = s.split("=", 1)
        overwrites[k.strip()] = v.strip()
    return overwrites


def main() -> int:
    global WARNINGS
    WARNINGS = WarningCollector()

    parser = _build_parser()
    args = parser.parse_args()

    if args.check:
        run_self_check()
        return 0

    if args.lint:
        if not os.path.exists(args.lint):
            print(f"错误：文件不存在 — {args.lint}")
            return 1
        return run_lint(args.lint)

    if args.diff:
        f1, f2 = args.diff
        for fp in (f1, f2):
            if not os.path.exists(fp):
                print(f"错误：文件不存在 — {fp}")
                return 1
        return run_diff(f1, f2)

    if args.audit:
        design_path, src_dir = args.audit
        if not os.path.exists(design_path):
            print(f"错误：DESIGN.md 文件不存在 — {design_path}")
            return 1
        if not os.path.isdir(src_dir):
            print(f"错误：源码目录不存在 — {src_dir}")
            return 1
        rc = run_audit(design_path, src_dir)
        if rc > 0:
            print(f"💡 提示：违规颜色可能是 DESIGN.md 缺失的令牌，或被忽略的第三方库颜色")
        return 0 if rc == 0 else 1

    if args.import_local:
        rc = _run_import_local(args.import_local, args.output)
        return 0 if rc == 0 else 1

    # Master + Page 分层（参考 nextlevelbuilder/ui-ux-pro-max-skill 的 Master+Overrides 模式）
    if args.master:
        master_path = args.master
        if not os.path.exists(master_path):
            print(f"错误：Master 文件不存在 — {master_path}")
            return 1
        page_name = args.page or "default"
        # 将 --set 传入 modify，覆盖 master DESIGN.md 中的颜色
        overwrites = _parse_overwrites(args.set)
        # 如果用户没显式 --set，自动添加 page-specific name
        if "name" not in overwrites and page_name != "default":
            overwrites["name"] = f"{Path(master_path).stem} - {page_name}"
        output_name = f"{Path(master_path).stem}_{page_name}.md"
        output_path = resolve_output_path(args.output or output_name)
        try:
            modify_design_md(master_path, overwrites, output_path, args.spacing_base or 4)
            print(f"   Master: {master_path}")
            print(f"   Page:   {page_name}")
            print(f"   覆盖:   {overwrites}")
            print(f"✅ 已生成页面级 DESIGN.md: {output_path}")
            return 0
        except (ValidationError, ValueError) as e:
            print(f"错误：{e}")
            return 1

    # 反向工程模式：生成 DESIGN.md 后可接续 --export / --visualize
    analysis_done = False
    if args.import_file:
        rc = _run_import(args.import_file, args.output)
        if rc != 0:
            return rc
        analysis_done = True
        if not args.export and not args.visualize:
            return 0

    if args.analyze:
        rc = _run_analyze_screenshot(args.analyze, args.output or "DESIGN.md")
        if rc != 0:
            return rc
        analysis_done = True
        if not args.export and not args.visualize:
            return 0

    # 迭代修改模式：未显式传 --output 时默认覆盖被 --modify 的文件本身
    if args.modify:
        if not os.path.exists(args.modify):
            print(f"错误：要修改的文件不存在 — {args.modify}")
            return 1
        try:
            overwrites = _parse_overwrites(args.set)
            output_path = resolve_output_path(args.output or args.modify)
            modify_design_md(args.modify, overwrites, output_path, args.spacing_base or 4)
            return 0
        except (ValidationError, ValueError) as e:
            print(f"错误：{e}")
            return 1

    # 名称校验（分析模式下可跳过，直接进入导出）
    if not analysis_done:
        if not args.name or not args.name.strip():
            print("错误：--name 不能为空")
            return 1

    try:
        output_path = resolve_output_path(build_output_path(args.output or "DESIGN.md", args.timestamp))
    except (ValidationError, ValueError) as e:
        print(f"错误：{e}")
        return 1

    if not analysis_done:
        # 模板应用
        if args.template:
            tpl = apply_template(args.template, {
                "name": args.name,
                "description": args.description or None,
                "primary": args.primary,
                "secondary": args.secondary,
                "background": args.background,
                "text": args.text,
                "font": args.font,
                "tone": args.tone,
            })
            args.primary = args.primary or tpl["primary"]
            args.secondary = args.secondary or tpl["secondary"]
            args.background = args.background or tpl["background"]
            args.text = args.text or tpl["text"]
            args.font = args.font or tpl["font"]
            args.tone = args.tone or tpl["tone"]
            args.description = args.description or tpl["desc"]

        # 非模板默认值
        args.primary = args.primary or DEFAULT_PRIMARY
        args.secondary = args.secondary or DEFAULT_SECONDARY
        args.background = args.background or DEFAULT_BACKGROUND
        args.text = args.text or ""
        args.tone = args.tone or "专业"

        # 自动文字色
        if not args.text:
            args.text = auto_text_color(args.background)

        # 多语言字体
        args.font = detect_preferred_font(args.name, args.description, args.font)

        # 校验强调色
        if args.accent_colors:
            valid = []
            for c in args.accent_colors:
                cleaned = c.strip()
                try:
                    normalize_to_hex(cleaned)
                    valid.append(cleaned)
                except ValueError as e:
                    WARNINGS.add(f"[accent-colors] 格式非法（{c}）: {e}，已跳过")
            args.accent_colors = valid

        # 构建 DESIGN.md
        try:
            content, theme = build_design_md(args)
        except Exception as e:
            print(f"错误：生成 DESIGN.md 失败 — {e}")
            return 1

        # 路径安全与写入
        try:
            safe_write(output_path, content)
        except ValidationError as e:
            print(f"错误：{e}")
            return 1
        except (IOError, PermissionError, OSError) as e:
            print(f"写入文件失败：{e}")
            print(f"  请检查输出路径是否可写：{output_path}")
            return 1

        # 汇总输出
        theme_label = "dark" if theme.is_dark else "light"
        print(f"DESIGN.md generated: {output_path}")
        print(f"   Name: {args.name}")
        if args.template:
            print(f"   Template: {args.template}")
        print(f"   Theme: {theme_label}")
        print(f"   Tone: {args.tone}")
        print(f"   Primary: {theme.primary}")
        print(f"   Background: {theme.background}")
        print(f"   Text: {theme.text}")

    # 色板可视化（仅正向生成模式）
    palette_path = None
    if not analysis_done and args.visualize:
        try:
            palette_path = generate_palette_svg(theme, args.name, output_path, args.tone, args.accent_colors)
            if palette_path:
                print(f"\n   Palette: {palette_path}")
        except Exception as e:
            WARNINGS.add(f"SVG 色板生成失败：{e}")

    # 代码导出
    if args.export:
        for fmt in sorted(set(args.export)):
            print(f"\n  Exporting tokens as {fmt}:")
            handle_export(output_path, fmt)

    if WARNINGS:
        print(f"\n  {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(w)

    if not analysis_done:
        print(f"\n   Color tokens: 20+")
        print(f"   Typography tokens: 12")
        print(f"   Components: 25+")
        print(f"   Shadows: 6 levels")
        print(f"   Spacing: 9 levels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
