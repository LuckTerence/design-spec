---
name: design-spec
description: "根据品牌/产品描述自动生成 DESIGN.md 设计规范文档。当用户提到'生成设计规范'、'设计系统'、'品牌规范'、'DESIGN.md'、'设计令牌'、'Design Tokens'、'Design System'、'生成 Design Spec'时使用。不要用于需要手动设计或已有完整设计稿的场景。"
agent_created: true
version: 1.0.0
author: LuckTerence
homepage: https://github.com/LuckTerence/design-spec
license: Apache-2.0
tags:
  - design
  - design-system
  - design-tokens
  - brand
  - color
  - despec
---

## 干什么的

给你一个品牌名、一个主色、一个风格，就能自动生成一份完整的 DESIGN.md 设计规范。不用自己手写几百行的颜色令牌和组件定义了。

## 怎么用

你可以说：

- "帮我生成一个 SaaS 后台的设计规范，蓝色系"
- "给这个品牌 #4F46E5 做主色，做一份设计系统"
- "分析这张截图，提取颜色生成 DESIGN.md"
- "帮我把这个网站的设计系统抓取出来"
- "把 DESIGN.md 里的主色改成 #FF6600"
- "校验一下这份 DESIGN.md 符不符合规范"
- "对比一下这两版设计规范改了什么"

我会反问你品牌名称、想要的感觉、有没有参考色，然后直接跑脚本生成。

## 能生成什么

- 20+ 颜色令牌、12 级字体、25+ 组件定义
- 深色主题自动适配、中文字体自动匹配
- 色板 SVG 预览图
- 支持导出 Tailwind / CSS / DTCG 格式
- 改一个主色，所有关联的 hover、active、disabled 色全自动同步
- 校验（`--lint`）和版本比对（`--diff`）直接调用官方 `@google/design.md` CLI，不重复造轮子；未安装该 CLI 时会提示安装方式，这两项没有本地兜底

## 自带 12 个行业模板

enterprise（SaaS）、ecommerce（电商）、finance（金融）、creative（内容）、healthcare（医疗）、education（教育）、gaming（游戏）、food-beverage（餐饮）、real-estate（房产）、travel（旅游）、social-media（社交）、developer-tools（开发者工具）。

## 命令速查

```bash
# 基础用法
python scripts/generate_design_spec.py --name "品牌" --primary "#4F46E5"

# 选模板
python scripts/generate_design_spec.py --name "店铺" --template ecommerce

# 深色主题
python scripts/generate_design_spec.py --name "App" --background "#0D1117" --text ""

# 截图分析
python scripts/generate_design_spec.py --analyze screenshot.png

# 导入外部工具（designlang 等）产出的 DESIGN.md 并重新对齐
python scripts/generate_design_spec.py --import designlang_output.md

# 改主色，派生色自动更新
python scripts/generate_design_spec.py --modify DESIGN.md --set "primary=#FF6600"

# 导出为 Tailwind / CSS / DTCG（优先走官方 CLI，不可用时本地兜底）
python scripts/generate_design_spec.py --name "App" --export tailwind --export css

# 用官方 Linter 校验已生成的文件
python scripts/generate_design_spec.py --lint DESIGN.md

# 对比两个版本的差异
python scripts/generate_design_spec.py --diff DESIGN_old.md DESIGN_new.md
```

完整字段示例见 `references/DESIGN.md`。
