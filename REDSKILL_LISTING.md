# Design Spec Generator — RedSkill 上架文案

## 一句话卖点

> **给一个品牌名、一个主色、一个风格，秒级生成完整的 DESIGN.md 设计规范。**  
> 离线、隐私友好，不依赖任何第三方 API。

---

## 详细描述

Design Spec Generator 是一个 **文本 → DESIGN.md 设计规范生成引擎**。你不需要打开 Figma，不需要手写几百行颜色令牌和组件定义——只要告诉我品牌叫什么、主色是什么、想要什么风格，一条命令跑完，直接得到一份结构完整的 `DESIGN.md` 文件。

### 它能做什么

| 能力 | 说明 |
|------|------|
| **文本生成规范** | 给 `--name` `--primary` `--template`，自动输出 20+ 颜色令牌、12 级字阶、25+ 组件定义 |
| **12 行业模板** | enterprise(SaaS)、ecommerce(电商)、finance(金融)、creative(内容)、healthcare(医疗)、education(教育)、gaming(游戏)、food-beverage(餐饮)、real-estate(房产)、travel(旅游)、social-media(社交)、developer-tools(开发工具) |
| **截图取色分析** | 给一张截图，`--analyze` 自动提取主色+次要色+背景色，生成完整规范 |
| **深色主题适配** | 指定深色背景色，自动生成深色优先的色板与对比度校验 |
| **外部导入对齐** | `--import` 导入 designlang 等工具输出的 DESIGN.md，重新对齐颜色（hex/rgb/oklch 归一、派色再生、WCAG 校验），正文无损 |
| **修改主色自动派生** | `--modify` 改一个主色，所有 hover/active/disabled/border 色全部自动同步 |
| **多格式导出** | `--export tailwind/css/dtcg`，优先走官方 `@google/design.md` CLI |
| **规范校验** | `--lint` 调用 Google 官方 linter；`--diff` 版本对比 |

### 技术特性

- **离线运行**：所有计算在本地完成，无需联网，无需 API Key
- **成熟底层**：颜色数学/截图取色/对比度计算全部基于 coloraide + colorthief + Pillow
- **规范对齐**：输出遵循 Google Labs `@google/design.md` 格式（YAML frontmatter + Markdown body）
- **轻量部署**：Python 3.12+ 一键 pip install，无外部服务依赖

### 适用场景

- AI Chat 助手（作为 WorkBuddy / CodeBuddy Skill）
- 品牌视觉设计前期，快速产出参考规范
- UI 设计师快速生成 Design Tokens 示例
- 教学演示——展示 Design System 的结构与逻辑

---

## 截图说明

建议在 RedSkill 市场上传以下 4 张截图：

### 截图 1：生成示例（推荐：SaaS 后台模板）
> 展示 `generate_design_spec.py --name "数智后台" --primary "#4F46E5" --template enterprise` 生成的 DESIGN.md 头部，包含 Name / Colors / Typography 三个块，重点展示颜色令牌表格。

**推荐尺寸**：1280×800px 或 1920×1200px  
**内容提示**：截取终端输出 + DESIGN.md 头部，叠加标注 "20+ 色板 / 12 级字阶 / 25+ 组件"

### 截图 2：截图分析功能
> 展示 `--analyze screenshot.png` 运行过程，终端输出提取到的颜色列表和生成结果头部。

**内容提示**：左侧展示被分析的截图缩略图（标注提取到的颜色），右侧展示生成结果中的 Colors 块

### 截图 3：--import 外部对齐
> 展示 `--import designlang_output.md` 运行效果，终端输出 "Colors realigned" 摘要。

**内容提示**：截取 import 前后 colors 块对比（带色号归一化前后差异），或直接用 diff 标注

### 截图 4：多行业模板一览
> 用拼贴图展示 12 个模板生成的 DESIGN.md 各截一段头部，突出不同行业色板差异。

**内容提示**：4×3 或 3×4 网格，每个格子里是模板名 + 生成结果头部 + 主色色板

---

## 使用示范（5 个最常用场景）

### 场景 1：一句话生成

> **用户说**："帮我生成一个电商设计规范，橙红色系"
>
> **运行**：
> ```bash
> python scripts/generate_design_spec.py \
>   --name "潮品电商" \
>   --primary "#FF6B35" \
>   --template ecommerce
> ```
>
> **输出**：`DESIGN.md` —— 含完整色板、字阶、按钮/卡片/导航/表单等组件定义

### 场景 2：从截图生成

> **用户说**："分析这个 UI 截图，提取它的设计规范"
>
> **运行**：
> ```bash
> python scripts/generate_design_spec.py \
>   --analyze screenshot.png \
>   --name "参考品牌"
> ```
>
> **输出**：自动提取主色/次要色/背景色 + 基于 12 模板风格生成规范

### 场景 3：改主色，全量派生自动更新

> **用户说**："把 DESIGN.md 的主色改成 #FF6600，其他色自动适配"
>
> **运行**：
> ```bash
> python scripts/generate_design_spec.py \
>   --modify DESIGN.md \
>   --set "primary=#FF6600"
> ```
>
> **输出**：`DESIGN_modified.md` —— 主色 + 所有派生色（hover/active/disabled/border/background）同步更新

### 场景 4：导入外部工具结果

> **用户说**："帮我把 designlang 抓出来的网站设计重新对齐规范"
>
> **运行**：
> ```bash
> python scripts/generate_design_spec.py \
>   --import designlang_output.md
> ```
>
> **输出**：`designlang_output_realigned.md` —— 颜色归一为 hex，派生色补全，正文无损

### 场景 5：导出产物

> **用户说**："生成的规范能不能导出 Tailwind 配置？"
>
> **运行**：
> ```bash
> python scripts/generate_design_spec.py \
>   --name "我的品牌" \
>   --export tailwind
> ```
>
> **输出**：`DESIGN_tailwind.md` + `DESIGN_tailwind.css`（Tailwind 色阶 + CSS 自定义属性）

---

## 技术栈

| 依赖 | 用途 |
|------|------|
| coloraide 8.10+ | 颜色数学、OKLCH 插值、WCAG 对比度 |
| colorthief 0.2+ | 截图取色（MMCQ 算法） |
| Pillow 12+ | 图像处理基础 |
| @google/design.md CLI | 规范校验、差异对比、格式导出（可选安装） |

---

## 许可证

Apache 2.0 © LuckTerence
