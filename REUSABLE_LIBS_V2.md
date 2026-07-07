# design-spec 模块复用评估报告 v2

> 执行时间：2026-07-07  
> 前提：此前 REUSABLE_LIBS.md 已完成 18 仓库 + 1 竞品调研，本次聚焦 **"代码中仍属自研、可否进一步复用第三方轮子"** 的深层扫描。  
> 方法与范围：阅读全部源代码（`generate_design_spec.py` ~1980 行 + `analyze_screenshot.py` ~130 行），逐函数评估复用可能性，结合 GitHub / PyPI / npm 实时数据。

---

## 1. 当前复用全景（已完成替换）

| 模块 | 原始方案 | 替换方案 | 状态 |
|------|---------|----------|------|
| 颜色数学（hex/rgb/oklch ↔ hex） | `webcolors` + 手写字典 + `colorsys` | **`coloraide`** | ✅ 已完成 |
| WCAG 对比度 | 手写 sRGB 线性化 | **`coloraide.contrast(method="wcag21")`** | ✅ 已完成 |
| OKLCH 插值与色派生 | 手写色彩空间变换 | **`coloraide.interpolate()`** | ✅ 已完成 |
| 截图取色 | `sklearn KMeans` + `numpy` | **`colorthief`**（MMCQ） | ✅ 已完成 |
| URL 抽取 | 自研 `analyze_url.py` + `extraction.js` | **委托 designlang**（`--import` 模式） | ✅ 已完成 |
| lint / diff / export | — | 调用 **`@google/design.md` CLI** | ✅ 已完成 |

---

## 2. 剩余自研模块逐一评估

### 2.1 `parse_yaml_frontmatter`（第 1236-1265 行，~30 行）

| 维度 | 评估 |
|------|------|
| **功能** | 用正则解析 DESIGN.md 的 YAML frontmatter，提取 name/colors/font |
| **替代方案** | **`PyYAML`（`yaml.safe_load`）** |
| **Stars / 生态** | PyPI 稳定版，月下载 ~1.2 亿次，Python 生态 YAML 事实标准 |
| **重复造轮子** | **是**。`---\nkey: "value"\n---` 是标准 YAML，当前只取 6-7 个字段却维护了一套完整解析器 |
| **隐蔽风险** | 正则 `(.*?)` 在嵌套 YAML（`typography:` 含子块）时可能越界或漏匹配 |
| **成本** | 极低：pip install PyYAML + ~10 行改写 |
| **收益** | 健壮性提升，消除正则边界 bug，后续修 YAML 相关 issue 不再需要手写 |

### 2.2 `generate_yaml_frontmatter`（第 496-700+ 行，~200 行 YAML 序列化）

| 维度 | 评估 |
|------|------|
| **功能** | 用字符串拼接构建 YAML frontmatter（colors / typography / rounded / spacing 等） |
| **替代方案** | **`PyYAML` + `coloraide`**（构建 Python dict → `yaml.dump`） |
| **重复造轮子** | **部分是**。数据本身是逻辑（派生色生成、模板映射），数据→YAML 表示是重复造轮子 |
| **隐蔽风险** | `escape_yaml` 函数（第 159 行）手动处理了换行/控制字符/方向字符等多种边缘情况——但标准 `yaml.dump` + 双引号 `default_style='"'` 原生就处理了 |
| **成本** | 中：需要将 ~90 行 `lines.append(f'  {k}: "{v}"')` 改为 dict 构建，测试回归 |
| **收益** | 消除 YAML 转义维护成本；支持复杂 YAML 结构（嵌套、列表），为后续扩展铺路 |

### 2.3 `build_color_theme`（第 449-493 行，~45 行）

| 维度 | 评估 |
|------|------|
| **功能** | 从 primary/secondary/background 推导 surface/border/disabled 等 10 个派生色 |
| **替代方案** | **无现成库**。coloraide 已用于 `darken_color` / `lighten_color`，但"按背景亮度自动选派生公式"是设计系统特有的业务规则 |
| **重复造轮子** | **否**。这不是颜色数学，是设计决策——不同设计系统有不同规则。如需更强能力，可借鉴 **adobe/leonardo** 算法（JS，Python 无移植） |

### 2.4 `generate_markdown_body`（第 789-1030 行，~242 行）

| 维度 | 评估 |
|------|------|
| **功能** | 生成 Markdown 正文（Brand Voice / Components / 核心指标 / 最佳实践 等章节） |
| **替代方案** | **无**。25+ 组件的描述文本和属性定义是本项目的核心数据资产 |
| **重复造轮子** | **否**。这是护城河 |

### 2.5 `generate_palette_svg`（第 1108-1209 行，~102 行）

| 维度 | 评估 |
|------|------|
| **功能** | 用字符串拼接生成色板 SVG 预览图 |
| **替代方案** | 可引入 **`svgwrite`** 或直接保留字符串拼接 |
| **重复造轮子** | **部分是**。但 102 行内容简单（颜色方块 + 标签），替换成本 > 收益 |
| **建议** | **保留**，不引入额外依赖 |

### 2.6 `_fallback_export` + `_extract_tokens_fallback`（第 1367-1445 行，~80 行）

| 维度 | 评估 |
|------|------|
| **功能** | `@google/design.md` CLI 不可用时，本地兜底导出 CSS/Tailwind |
| **替代方案** | **`style-dictionary`** npm 包（4.7K★）已集成，可将其设为硬依赖（`npx style-dictionary`） |
| **重复造轮子** | **是**。字符串拼接 CSS 不如让 style-dictionary 原生生成 |
| **成本** | 需要 `npx` 确保 style-dictionary v4 可用（当前已在 run_lint 中使用 npx） |
| **收益** | 导出格式更标准、支持更多平台输出 |

### 2.7 行业模板（`TONE_MAP` / `apply_template`，~50 行）

| 维度 | 评估 |
|------|------|
| **功能** | 12 模板预设（颜色偏移 + 语气描述） |
| **替代方案** | **无**。这是定制数据 |
| **重复造轮子** | **否** |

### 2.8 `detect_preferred_font`（第 1223-1233 行，~11 行）

| 维度 | 评估 |
|------|------|
| **功能** | 根据品牌名/描述匹配中文字体 |
| **替代方案** | **`fonttools`**（5.1K★） |
| **重复造轮子** | **否**。当前实现虽简单（关键词匹配），但 fonttools 主要用于字形分析，对字体名称猜测无直接帮助。10 行自研逻辑足以 |

---

## 3. 本次新发现的 GitHub 项目

### 3.1 `Easy-Hexford/design-md-generator`

| 字段 | 值 |
|------|-----|
| Stars | **2** |
| 最后推送 | 2026-04-09（创建当天） |
| 语言 | JavaScript |
| 许可证 | **无** |
| **结论** | 项目太新太小，无法作为可靠依赖。但其"本地源码→DESIGN.md"的 **local mode** 概念有价值——如果该仓库后续增长，可作为 `--import` 的 Node.js 备选后端 |

### 3.2 `retostauffer/python-colorspace`

| 字段 | 值 |
|------|-----|
| PyPI | `colorspace` |
| 定位 | **数据可视化**调色板（HCL 模型，仿 R colorspace 包） |
| 验证 | 生成定性/顺序/发散调色板（如 ColorBrewer、viridis） |
| **与本项目关系** | **不适合**：不支持"从单色生成设计系统色板"，无和谐配色（互补/类似色），WCAG 对比度功能较弱。本项目已有 coloraide，功能更强 |

### 3.3 `gddickinson/colour-palette`

| 字段 | 值 |
|------|-----|
| 定位 | Python 色轮和谐配色生成器（互补色/三色系/四色系） |
| **评估** | 小项目，未评估其 API 质量。但**概念有益**——如果本项目需要"从 primary 自动推荐 secondary"，类似项目的颜色和谐算法可参考 |
| **替代方案** | 当前 secondary 靠用户输入或预设模板，无自动推荐。可作为后续增强方向参考 |

---

## 4. 结论：唯一真正缺失的轮子

```
┌──────────────────────────────────────────────────────────────────┐
│ 经过逐模块扫描，本项目 1980 行脚本中：                            │
│                                                                  │
│  ✅ 颜色数学 / WCAG / 截图取色 / URL 抽取 → 已全部替换为成熟轮子 │
│  ❌ 数据资产（12 模板 / 25+ 组件 / 字阶）→ 不可替换，这是护城河    │
│  ❌ 设计决策逻辑（派生色公式 / 主题策略）→ 不可替换，业务规则       │
│                                                                  │
│  唯一可替换但未替换的：                                           │
│  ──────────────────────────────────────────                       │
│  📌 YAML frontmatter 解析（parse_yaml_frontmatter）              │
│     30 行正则 → 用 PyYAML 3 行解决                               │
│                                                                  │
│  值得替换但收益中等的：                                           │
│  ─────────────────────────                                       │
│  📌 YAML frontmatter 生成（generate_yaml_frontmatter）            │
│     200 行字符串拼接 → 用 yaml.dump 减少 ~100 行                  │
│  📌 导出兜底（_fallback_export）                                  │
│     80 行 CSS 拼接 → 让 style-dictionary 原生生成                │
└──────────────────────────────────────────────────────────────────┘
```

### 建议执行顺序

| 优先级 | 任务 | 工作量 | 收益 |
|--------|------|--------|------|
| **P0** | `parse_yaml_frontmatter` 替换为 `PyYAML` | ~15 行代码 | 消除正则边界 bug，提升健壮性 |
| **P1** | `generate_yaml_frontmatter` 输出改用 `yaml.dump` | ~100 行重构 | 消除 escape_yaml 维护成本 |
| **P2** | `_fallback_export` 改用 `style-dictionary` 原生生成 | ~50 行 | 导出更标准，消除 CSS 拼接 |

---

## 5. 数据来源

- GitHub REST API：`api.github.com/repos/{owner}/{repo}`（stargazers_count/pushed_at/license）
- PyPI：`pypi.org/project/{package}` / pip show
- 源码阅读：`scripts/generate_design_spec.py`（1980 行） + `scripts/analyze_screenshot.py`（130 行）
- 采集日期：2026-07-07
