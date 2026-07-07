# design-spec

一个从品牌描述、截图或网页生成 `DESIGN.md` 设计规范文件的小工具。

输出的 `DESIGN.md` 遵循 [Google Labs design.md](https://github.com/google-labs-code/design.md) alpha 规范，包含机器可读的 YAML 设计令牌和人类可读的 Markdown 使用说明。

## 能做什么

- **描述生成**：输入品牌名称、调性、色板，直接输出完整的设计规范
- **截图分析**：上传一张截图，自动提取主色、背景色、文字色等令牌
- **网页采样**：给出一个网址，从真实页面中提取颜色、字体、圆角等样式
- **代码导出**：把 `DESIGN.md` 转成 Tailwind 主题、CSS 变量或 DTCG JSON
- **校验与比对**：`--lint`/`--diff` 直接调用官方 [`@google/design.md`](https://github.com/google-labs-code/design.md) CLI 做规范校验和版本差异比较，不重复实现官方已有的规则

## 安装依赖

需要 Python 3.8+。核心功能只需要这几个 Python 包：

```bash
pip install coloraide pillow colorthief
```

可选工具：

- `designlang`（`npx @designlang/cli`）：用于真实网页的实时 DOM 采样；其输出可用本工具的 `--import` 重新对齐官方规范
- `@google/design.md` CLI：用于 `--export` 导出（不提供时会使用内置 fallback）、`--lint` 校验和 `--diff` 比对（这两项没有本地 fallback，未安装 CLI 会直接报错并提示安装方式）

## 快速开始

```bash
# 检查环境
python scripts/generate_design_spec.py --check

# 从描述生成
python scripts/generate_design_spec.py --name "MyBrand" --primary "#4F46E5"

# 使用行业模板
python scripts/generate_design_spec.py --name "MyShop" --template ecommerce

# 深色主题
python scripts/generate_design_spec.py --name "DarkApp" --background "#0D1117" --text ""

# 分析截图
python scripts/generate_design_spec.py --analyze screenshot.png

# 导入外部工具（designlang 等）产出的 DESIGN.md 并重新对齐
python scripts/generate_design_spec.py --import designlang_output.md

# 导出代码
python scripts/generate_design_spec.py --name "MyBrand" --export tailwind --export css

# 校验已生成的文件（调用官方 CLI）
python scripts/generate_design_spec.py --lint DESIGN.md

# 比对两个版本的差异（调用官方 CLI）
python scripts/generate_design_spec.py --diff DESIGN_old.md DESIGN_new.md
```

## 用法示例

### 正向生成

```bash
python scripts/generate_design_spec.py \
  --name "OceanPay" \
  --description "面向中小企业的支付控制台" \
  --primary "#1A73E8" \
  --secondary "#34A853" \
  --background "#FFFFFF" \
  --tone "专业" \
  --output DESIGN.md
```

### 行业模板

内置 12 种模板，可以直接用，也可以覆盖其中任意字段：

```bash
python scripts/generate_design_spec.py --name "FastShop" --template ecommerce --primary "#FF6600"
```

| 模板 | 场景 | 默认主色 |
|------|------|----------|
| `enterprise` | SaaS / B2B | #1A73E8 |
| `ecommerce` | 电商 / 营销 | #C2185B |
| `finance` | 银行 / 支付 | #0A753D |
| `creative` | 娱乐 / 内容 | #9C27B0 |
| `healthcare` | 医疗 / 在线问诊 | #0E7490 |
| `education` | 在线教育 / 知识付费 | #EA580C |
| `gaming` | 游戏 / 电竞社区 | #7C3AED |
| `food-beverage` | 餐饮 / 外卖 / 食谱 | #DC2626 |
| `real-estate` | 房产展示 / 物业管理 | #166534 |
| `travel` | 旅游出行 / 酒店预订 | #0284C7 |
| `social-media` | 社交平台 / 社区论坛 | #EC4899 |
| `developer-tools` | 开发者工具 / API 文档 | #0F766E |

### 迭代修改

修改已有的 `DESIGN.md`，派生色会自动同步更新：

```bash
python scripts/generate_design_spec.py --modify DESIGN.md --set "primary=#FF6600" --set "tone=活泼"
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `DESIGN.md` | 核心设计规范文档 |
| `*_palette.svg` | 色板可视化（需加 `--visualize`） |
| `*_tailwind.theme.json` | Tailwind 主题配置 |
| `*_tokens.css` | CSS 自定义属性 |
| `*_tokens.json` | DTCG 格式令牌 |

`*_tokens.json` 遵循 W3C Design Tokens 格式（DTCG），可以直接喂给 Style Dictionary、Tokens Studio 等已支持该格式的工具，产出 iOS / Android / SCSS 等更多平台的代码，不需要在本 Skill 里再手写这些导出器。

## 输入颜色格式

支持常见的 CSS 颜色格式：

- Hex：`#1A73E8`、`#fff`
- RGB / RGBA：`rgb(255, 87, 34)`、`rgba(0, 0, 0, 0.5)`
- HSL / HSLA：`hsl(210, 80%, 55%)`
- Oklch / Oklab：`oklch(70% 0.2 250)`、`oklab(60% -0.1 -0.2)`
- HWB：`hwb(210 20% 10%)`
- 命名颜色：`red`、`rebeccapurple`
- `transparent`

非法颜色会按字段回退到合理的默认值，并在终端提示警告。

## 安全与健壮性

- 输入颜色严格校验，越界或不可解析的值会被拒绝
- YAML 前置元数据中的字符串经过转义，防止注入
- 输出路径拒绝 `..` 段，避免写到预期目录之外
- 自动检测文字与背景、主色与白色的对比度，低于 WCAG AA 标准会提示警告
- 文件写入使用临时文件 + 原子替换，避免生成过程中断损坏文件

## 项目结构

```
design-spec/
├── scripts/
│   ├── generate_design_spec.py   # 主入口：生成、导出、自检、导入
│   └── analyze_screenshot.py     # 截图分析（colorthief + coloraide）
├── references/
│   └── DESIGN.md                 # 参考示例
├── SKILL.md                      # WorkBuddy Skill 描述
├── SECURITY_AUDIT_REPORT.md      # 安全审查与优化记录
├── README.md                     # 本文件
└── LICENSE                       # MIT
```

## 注意事项

- 截图分析与导入对齐均为启发式推断，复杂页面建议人工复核后再投入生产
- 网页（URL）采样委托 [designlang](https://github.com/Manavarya09/design-extract) 完成，其输出用 `--import` 重新对齐；纯文本生成无需任何浏览器依赖
- `--export` 优先使用 `@google/design.md` 官方 CLI，未安装时使用内置 fallback

## License

MIT — 详见 LICENSE 文件。
