---
version: "alpha"
name: "MyBrand (Reference Example)"
description: "参考示例：一个完整的 DESIGN.md 文件，供对照学习"

# ===== Colors =====
colors:
  primary: "#1A73E8"
  primary-hover: "#1557B0"
  primary-active: "#0D47A1"
  primary-light: "#E8F0FE"
  secondary: "#34A853"
  secondary-hover: "#2D9248"
  background: "#FFFFFF"
  surface: "#F8F9FA"
  surface-hover: "#F1F3F4"
  text-primary: "#1A1C1E"
  text-secondary: "#5F6368"
  text-disabled: "#9AA0A6"
  border: "#DADCE0"
  divider: "#E8EAED"
  error: "#D93025"
  success: "#188038"
  warning: "#F9AB00"
  info: "#1967D2"
  white: "#FFFFFF"
  black: "#000000"

# ===== Typography =====
typography:
  display-1:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 64px
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: -0.03em
  display-2:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: -0.02em
  heading-1:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 36px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.02em
  heading-2:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.25
  heading-3:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 22px
    fontWeight: 600
    lineHeight: 1.3
  subtitle:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.01em
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
  body-small:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0.02em
  button:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1
    letterSpacing: 0.02em
  code:
    fontFamily: "'JetBrains Mono', monospace"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.6
  overline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0.08em
    textTransform: uppercase

# ===== Rounded Corners =====
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
  2xl: 24px
  full: 9999px

# ===== Spacing =====
spacing:
  0: 0px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  3xl: 64px
  4xl: 96px

# ===== Elevation =====
elevation:
  none: none
  sm: "0px 1px 2px 0px rgba(0,0,0,0.05)"
  md: "0px 2px 4px 0px rgba(0,0,0,0.08), 0px 1px 2px -1px rgba(0,0,0,0.06)"
  lg: "0px 4px 8px 0px rgba(0,0,0,0.08), 0px 2px 4px -2px rgba(0,0,0,0.06)"
  xl: "0px 8px 16px 0px rgba(0,0,0,0.08), 0px 4px 8px -4px rgba(0,0,0,0.06)"
  2xl: "0px 16px 24px 0px rgba(0,0,0,0.10), 0px 8px 16px -8px rgba(0,0,0,0.06)"

# ===== Components =====
components:
  button-primary:
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
    padding: 10px 12px
  input-focus:
    backgroundColor: "{colors.background}"
    textColor: "{colors.primary}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  badge:
    rounded: "{rounded.full}"
    padding: 2px 8px
    typography: "{typography.caption}"
---

<!--
Reference: google-labs-code/design.md specification (alpha)
-->

## Overview

这个文件是符合 DESIGN.md 规范的完整参考示例。它展示了设计系统的完整结构：从色彩、字体到组件的所有层级。

## Colors

色板使用语义化命名。前缀 `primary`、`secondary` 指示角色，后缀 `-hover`、`-active`、`-light` 指示状态。中性色 `surface`、`border`、`divider` 构成页面骨架。

## Typography

字体层级从 display-1 到 overline 覆盖了从大屏标题到辅助标签的全部文本场景。遵循"可用 token 命名而非硬编码字号"的原则。

## Layout & Spacing

4px 基准网格，间距值为 4 的倍数。组件内部用 xs/sm，组件之间用 md/lg，页面分区用 xl 及以上。

## Elevation & Depth

阴影使用 rgba 格式确保叠加时的正确混合，避免使用不透明的纯黑阴影。

## Components

组件属性支持令牌引用语法 `{colors.primary}`，实现设计语言的一致引用。组件变体通过语义化名称区分（如 button-primary-hover）。

## Do's and Don'ts

始终使用令牌引用而非硬编码值。正文避免使用纯黑 #000000。不要跳级使用字体层级。
