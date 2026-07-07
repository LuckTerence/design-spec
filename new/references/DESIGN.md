---
version: "alpha"
name: "Design Spec Reference"
description: "A complete design system reference example demonstrating all 25+ components, 12 typography scales, 9 spacing levels, and 6 shadow levels following the Google Labs design.md specification."

# ===== Colors =====
colors:
  primary: "#4f46e5"
  primary-hover: "#433bc2"
  primary-active: "#3b34ab"
  primary-light: "#6961e8"
  secondary: "#10b981"
  secondary-hover: "#0d9d6d"
  background: "#ffffff"
  surface: "#f9f9f9"
  surface-hover: "#f2f2f2"
  text-primary: "#1a1c1e"
  text-secondary: "#727272"
  text-disabled: "#b2b2b2"
  border: "#d8d8d8"
  divider: "#e0e0e0"
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
  overline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0.08em
  code:
    fontFamily: "'Inter-Mono', 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.6

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
---

<!--
Generated: 2026-07-04 15:07:21
Generator: design-spec Skill (WorkBuddy)
Based on: google-labs-code/design.md specification (valpha)
-->

## Overview

Design Spec Reference 的设计系统围绕以下核心原则构建：

- **清晰、精确、可信赖。我们通过克制的视觉语言传递专业度。**
- **一致性**：所有组件共享统一的设计语言，确保用户在不同页面间获得连贯体验
- **可访问性**：色彩对比度不低于 WCAG AA 标准，所有交互元素有明确焦点状态
- **可扩展性**：设计令牌体系支持从单一页面到复杂应用的无缝扩展



> 本文件符合 Google Labs design.md valpha 规范，可作为 AI 编码代理的设计参考。


## Colors

色板系统分为语义色和中性色两大类。

### 语义色

- **Primary（#4f46e5）**：品牌主色，用于主要行动按钮、链接、活动态元素
- **Primary Hover（#433bc2）**：Primary 的悬停状态
- **Primary Active（#3b34ab）**：Primary 的按下状态
- **Primary Light（#6961e8）**：Primary 的浅色背景态，用于标签或背景填充
- **Secondary（#10b981）**：辅助色，用于次要行动按钮、成功状态反馈

### 语义功能色

- **Error（#D93025）**：错误状态、必填校验
- **Success（#188038）**：成功状态、完成确认
- **Warning（#F9AB00）**：警告状态、需要关注的信息
- **Info（#1967D2）**：提示信息、引导性内容

### 中性色

背景色（#ffffff）、表面色（#f9f9f9）、文字色（#1a1c1e）、边框色、分割线色构成页面的基础层次结构。

### 使用规则

- **主色使用率**：主色在界面中的占比不超过 15%，避免视觉疲劳
- **对比度要求**：所有文字与背景的对比度不低于 4.5:1（AA 标准），大号文字不低于 3:1
- **色盲友好**：不使用纯红色或纯绿色作为唯一的区分信息手段


## Typography

采用 **Inter, system-ui, sans-serif** 作为首选字体族，等宽字体用于代码场景。

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


## Layout & Spacing

### 间距体系

采用 **4px 基准网格**，所有间距值均为 4px 的倍数：

| Token | 值 | 场景 |
|-------|-----|------|
| xs | 4px | 图标与文字间距 |
| sm | 8px | 组件内元素间距 |
| md | 16px | 组件间距、段落间距 |
| lg | 24px | 区块间距 |
| xl | 32px | 大区块间距 |
| 2xl | 48px | 页面分区间距 |
| 3xl | 64px | 页面顶部/底部间距 |
| 4xl | 96px | 超大留白 |

### 布局原则

- **响应式断点**：768px（平板）、1024px（桌面）、1440px（宽屏）
- **内容最大宽度**：1200px，超出时居中留白
- **网格**：12 列网格系统，列间距 24px


## Elevation & Depth

阴影层级通过 Z 轴深度传达元素的层级关系。本设计采用暗色阴影阴影体系：

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


## Shapes

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


## Components

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
| default | 1px solid #d8d8d8 边框 |
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
- **Progress**：surfate 底 6px 轨道 + primary 填充条
- **Skeleton**：surface 底色 sm 圆角占位块
- **Empty State**：居中 text-secondary，3xl 垂直内边距

### 布局（Container）

内容区最大宽度 1200px，水平居中，内边距 md (16px)。


## Do's and Don'ts

### Do's

- 使用设计令牌引用而非硬编码值（如 `{{colors.primary}}` 而非 `"#4f46e5"`）
- 遵循字体层级约束，从 display-1 到 body 按需递减
- 确保所有交互元素有明确的 hover 和 focus 状态
- 在浅色背景上使用深色文字
- 对于彩色按钮，hover 状态应比默认加深 15%

### Don'ts

- 不要在一个页面中使用超过 3 种强调色
- 不要在正文中使用纯黑色（#000000）——使用 text-primary（#1a1c1e）
- 不要直接修改设计令牌的值——如需变更，更新 DESIGN.md 中的定义
- 不要在卡片上叠加阴影再叠加阴影——嵌套元素不应自带入额外的阴影层级
- 不要为文字内容随意指定字号——必须从字体层级中选择

