---
name: design-spec
description: 根据品牌描述自动生成 DESIGN.md 设计规范文档（兼容 Google labs/design.md 格式）。输入品牌名称、设计风格、色板偏好等信息，输出结构化设计令牌规范，含色板、字体、间距、圆角、组件准则。
trigger: ["生成设计规范", "设计规范文件", "DESIGN.md", "品牌规范", "设计令牌", "设计系统", "视觉标识", "brand spec", "design tokens"]
references:
  - references/DESIGN.md  # 完整示例文件
scripts:
  - scripts/generate_design_spec.py  # 自动生成脚本
---

# Design Spec — 设计规范生成 Skill

## 功能概述

基于 Google Labs [design.md](https://github.com/google-labs-code/design.md) 规范（24.6k stars），将用户对品牌/产品的文字描述自动转化为标准 `DESIGN.md` 文件，包含：

- **YAML 前置元数据**：机器可读的设计令牌（颜色、字体、间距、圆角、组件属性）
- **Markdown 正文**：人类可读的设计原则、用法说明、Do's and Don'ts

## 触发场景

当用户说以下语句时，自动加载本 Skill：

> "帮我生成一个设计规范文档"
> "给这个项目写 DESIGN.md"
> "我有个品牌想定义视觉规范"
> "帮我描述这个产品的设计系统"
> "生成设计令牌"

## 安全防护（P0 保障）

脚本内置 6 层防护：

| 防护层 | 说明 |
|--------|------|
| **输入校验** | CSS 颜色格式严格校验（hex/rgb/hsl/oklch/oklab/hwb/named-color/transparent），非法值按字段回退默认 + 显示警告 |
| **颜色归一化** | 所有 CSS 颜色真实转换为 sRGB hex，拒绝越界数值与不可解析格式 |
| **YAML 注入防护** | name/description/version 转义反斜杠、双引号、换行、行首控制字符与 Unicode 方向控制符 |
| **对比度检测** | WCAG AA 标准（≥4.5:1），自动检测 text-vs-background、text-vs-surface、primary-vs-white |
| **原子写入** | 临时文件 + os.replace 原子操作，中断不损坏目标文件 |
| **路径遍历防护** | 输出路径拒绝 `..` 段，防止写入预期目录之外 |

所有警告在生成结果末尾汇总展示，不会阻塞生成流程。

## P1 高级功能

### P1-1: 深色主题适配

根据背景色自动判断深浅主题，完整切换 17 项颜色推导逻辑：

| 差异项 | 浅色主题 | 深色主题 |
|--------|---------|---------|
| surface | 背景色 暗2% | 背景色 亮5% |
| text-secondary | 背景色 暗55% | 背景色 亮55% |
| border | 背景色 暗15% | 背景色 亮20% |
| 阴影颜色 | rgba(0,0,0,...) | rgba(255,255,255,...) |
| 文档文案 | "暗色阴影体系" | "亮色阴影体系" |

用户无需指定 `--theme`，脚本根据 `--background` 亮度自动判断。也可通过 `--text ""` 让脚本自动选择对比度合适的文字色。

### P1-2: 行业模板预设

| 模板 | 适用场景 | 主色 | 调性 | 字体 |
|------|---------|------|------|------|
| **enterprise** | SaaS / B2B 产品 | #1A73E8（蓝） | 专业 | Inter |
| **ecommerce** | 电商/营销页面 | #C2185B（玫红） | 活泼 | PingFang SC |
| **finance** | 银行/支付场景 | #0A753D（绿） | 专业 | SF Pro Text |
| **creative** | 娱乐/内容创作 | #9C27B0（紫） | 科技 | GT America |

用法：指定 `--template` 后，模板中的默认值与用户传入的自定义值自动合并，用户传入的优先级更高。

### P1-3: 版本化输出

启用 `--timestamp` 参数后，输出文件名自动追加日期后缀（如 `DESIGN_20260704.md`），防止多次生成互相覆盖。

## P2 差异化能力

### P2-1: 色板可视化（SVG）

启用 `--visualize` 参数后，生成 DESIGN.md 的同时输出一个同名 `*_palette.svg` 文件，包含 5 组 20+ 颜色的色板预览，直接显示颜色值、令牌名称和实际色块。

![色板预览示意图](https://via.placeholder.com/460x600/1e1e1e/e0e0e0?text=Palette+SVG+Preview)

### P2-2: 迭代修改

通过 `--modify` + `--set` 对已有 DESIGN.md 做局部更新。优化后采用"解析原参数 → 应用覆盖 → 重新生成"的方式，确保 primary-hover / primary-active / 语义功能色等派生字段同步更新：

```bash
# 修改主色（会同步更新 primary-hover / primary-active / primary-light）
python generate_design_spec.py --modify DESIGN.md --set "primary=#FF6600"

# 同时修改多个字段（tone 变更会同步更新 error/success/warning/info）
python generate_design_spec.py --modify DESIGN.md --set "primary=#E91E63" --set "tone=活泼"
```

支持修改的字段：primary / secondary / background / text / name / font / tone

### P2-3: 多语言字体自动匹配

当品牌名称或描述中包含中文字符时，自动切换为适合中文的字体族：

- 中文检测范围：CJK 统一表意文字（U+4E00–U+9FFF, U+3400–U+4DBF）
- 自动字体：`'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', system-ui, sans-serif`
- 英文检测未命中时：`Inter, system-ui, sans-serif`
- 用户已明确指定 `--font` 时不覆盖

验证结果：品牌名含"中文"时 fontFamily 自动切换为 PingFang SC

## 外部依赖（全开源、零密钥）

| 能力 | 依赖 | 许可证 |
|------|------|--------|
| 命名颜色解析 | webcolors | BSD |
| 颜色空间转换 | Python colorsys + 自研 Oklab/Oklch/HWB 转换 | PSF / MIT |
| 颜色聚类 | scikit-learn | BSD |
| 图像处理 | Pillow | HPND |
| 代码导出 | @google/design.md CLI (npm, 可选) | Apache 2.0 |

所有核心功能纯本地运行，无需任何 API 密钥。`--export` 优先调用官方 CLI，CLI 不可用时自动切换为本地 fallback。

## 执行流程

### 第一步：收集信息

通过自然对话逐轮获取以下信息（优先询问模板，再逐步细化）：

```
AI: 你想给什么项目或品牌生设计规范？
用户: [品牌名称]

→ 如果有参考模板
AI: 行业偏向哪个方向？企业SaaS / 电商营销 / 金融安全 / 创意媒体 / 从零自定义
用户: [选择模板或自定义]

→ 然后逐步细化
AI: 设计调性？专业 / 活泼 / 极简 / 科技 / 优雅
AI: 主色用什么色号？(留空则使用模板/默认色)
AI: 深色背景还是浅色背景？(留空则使用浅色)
...
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| **name** | 设计系统/品牌名称 | **必填** |
| **template** | 行业模板（enterprise/ecommerce/finance/creative） | 无 |
| **description** | 品牌或产品的简要描述 | 可选 |
| **tone** | 设计调性（专业/活泼/极简/科技/优雅） | 专业 |
| **primary** | 主色（CSS 颜色格式） | 按模板或 #1A73E8 |
| **secondary** | 辅助色（CSS 颜色格式） | 按模板或 #34A853 |
| **background** | 背景色（CSS 颜色格式） | 按模板或 #FFFFFF |
| **text** | 文字色（CSS 颜色格式，空=自动匹配背景色） | 自动推导 |
| **font** | 字体族 | 按模板或 Inter |
| **accent_colors** | 更多强调色（CSS 颜色格式，可传多个） | 空 |
| **timestamp** | 是否启用版本化输出 | 否 |
| **output** | 输出路径（拒绝 `..` 目录遍历） | DESIGN.md |

### 第二步：生成 DESIGN.md

运行脚本自动生成：

```bash
python ~/.workbuddy/skills/design-spec/scripts/generate_design_spec.py \
  --name "品牌名称" \
  --description "品牌描述" \
  --primary "#1A73E8" \
  --tone "专业" \
  --output DESIGN.md

# 使用电商模板 + 自定义主色
python ~/.workbuddy/skills/design-spec/scripts/generate_design_spec.py \
  --name "FastShop" --template ecommerce --primary "#FF6600" \
  --output DESIGN.md

# 深色主题 + 版本化输出
python ~/.workbuddy/skills/design-spec/scripts/generate_design_spec.py \
  --name "DarkApp" --background "#1A1C1E" --text "" \
  --output DESIGN.md --timestamp
```

### 第三步：展示与验证

1. 脚本输出会显示主题检测结果（light/dark）、模板（如有）和**警告摘要**
2. 使用 `present_files` 展示生成的 `DESIGN.md`
3. 向用户总结：
   - 主题模式（浅色/深色）与模板来源
   - 生成的令牌结构（色板规模、字体层级、组件数量）
   - 对比度检测结果（是否全部通过）
   - 注意事项（非法参数回退、低对比度警告）
4. **可选**：提示用户可通过官方 Linter 做完整验证：
   ```bash
   npx @google/design.md lint DESIGN.md
   ```
   输出格式校验结果（errors/warnings/info）和对比度报告。
5. 提示用户可以将文件放入项目根目录，供 AI 编码代理（如 Cursor、Claude Code）读取

## 输出文件格式

生成的 `DESIGN.md` 完全兼容 [google-labs-code/design.md](https://github.com/google-labs-code/design.md) 规范（版本 alpha），包含：

### YAML 前置元数据

```yaml
---
version: "alpha"
name: "ProjectName"
description: "品牌描述"
colors:
  primary: "#1A73E8"
  primary-hover: "#1557B0"
  secondary: "#34A853"
  ...
typography:
  heading-1:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 4px
  md: 8px
  lg: 16px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white}"
    rounded: "{rounded.md}"
    padding: 12px 24px
  ...
---
```

### Markdown 正文（8 个标准章节）

1. **Overview** - 品牌概述与设计原则
2. **Colors** - 色板使用规则与语义
3. **Typography** - 字体层级与文本样式
4. **Layout & Spacing** - 布局网格与间距体系
5. **Elevation & Depth** - 阴影层级与 Z 轴深度
6. **Shapes** - 圆角与形状指南
7. **Components** - 组件规范与变体
8. **Do's and Don'ts** - 使用建议与禁忌

### 深色主题差异

深色模式下：
- 阴影使用 `rgba(255,255,255,...)` 而非 `rgba(0,0,0,...)`
- surface 色高出背景色 5%（浅色模式低 2%）
- 文字色自动选择浅色（如 #E8EAED）
- Overview 章节增加深色主题说明

## 参考

- **Google Labs design.md 仓库**：<https://github.com/google-labs-code/design.md>
- **完整示例文件**：见 `references/DESIGN.md`
