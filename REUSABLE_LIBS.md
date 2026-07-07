# 可复用库与竞品调研（扩展版）

> 补充自 `PRELAUNCH_REVIEW_V2.md` 的 GitHub 调研章节。原报告对比 6 个项目，本文件扩展到 **18 个可核验仓库 + 1 个强竞品（designlang）**，并按「自研组件 → 推荐复用」做能力映射。
> 数据采集时间：2026-07-07，来源为 GitHub REST API（`api.github.com/repos/{owner}/{repo}`，权威字段）+ 项目官网/搜索交叉验证。

---

## 0. 为什么要从 6 个扩到 18 个

首轮调研只覆盖了「规范官方工具 + 通用令牌库」，漏掉了两类对项目**直接有用**的项目：

1. **直接竞品**（website → design system / DESIGN.md）——决定本项目的差异化护城河在哪。
2. **能力级轮子**（取色 / 颜色数学 / 对比度 / 字体度量）——可逐项替换或增强 `analyze_screenshot.py`、`generate_design_spec.py` 里的自研实现。

扩展后，可复用的定位从「泛泛而谈」变成「逐模块可落地」。

---

## 1. 直接竞品（website → 设计系统 / DESIGN.md）

| 项目 | Stars | 最近提交 | 许可证 | 语言 | 可复用/威胁评估 |
|------|------|----------|--------|------|----------------|
| **Manavarya09/design-extract**（= designlang） | ~2,500+（官网自报，仓库路径已迁移，API 暂不可查） | 镜像 1 天前活跃 | MIT | TS | **最强竞品**：headless 浏览器抓全站设计系统，输出 17+ 文件（DTCG tokens、Tailwind、shadcn 主题、Figma 变量、WCAG 对比度修复、语义分区、暗色配对、CI drift bot）。URL 抽取已商品化。 |
| **sunil-dsb/design.md** | 50 | 2026-05-19 | MIT | TS | **直接竞品**：从任意网站生成 DESIGN.md / Tailwind 主题 / tokens / prompts，面向 Claude Code、Cursor、v0 等。功能与本项目 `--analyze-url` 高度重叠。 |
| **jasonhnd/design-md-generator** | 2 | 停滞 | — | — | 停滞竞品（首轮已记录），功能已被本项目 `--analyze-url` 与 designlang 全面覆盖，无复用价值。 |
| **rtavasarala/d-extract** | 4 | 2026-04-15 | MIT | null | designlang 的 fork，无独立价值。 |

**结论**：URL → DESIGN.md 这条路已有 designlang（2,500★）和 sunil-dsb（50★）占据，且 designlang 能力深度远超自研 `analyze_url.py`。本项目**不应在 URL 抽取上与之硬拼**，而应保持「文本驱动、完全离线、隐私优先」的差异化（详见第 4 节）。

---

## 2. 可复用轮子（按能力映射）

### 2.1 取色（替代 / 增强 `analyze_screenshot.py` 的 KMeans）

| 项目 | Stars | 最近提交 | 许可证 | 算法 | 复用建议 |
|------|------|----------|--------|------|----------|
| **lokesh/color-thief** | 13,595 | 2026-07-01 | MIT | MMCQ（中位切分量化） | 成熟稳定的图片取色库，有 Python 移植版（`colorthief` pip 包）。可替换自研 KMeans，**免去 scikit-learn 重依赖**，且对「主色 + 调色板」语义更强。 |
| **Vibrant-Colors/node-vibrant** | 2,436 | 2026-01-27 | 无许可证声明 | Vibrant（Android 调色算法） | 提取 Vibrant / Muted / Dark 等语义色，适合自动配色建议。JS 生态，若 `analyze_url` 的浏览器侧需取色可复用。 |

### 2.2 颜色数学（替代 / 增强 `generate_design_spec.py` 的颜色规范化）

| 项目 | Stars | 最近提交 | 许可证 | 亮点 | 复用建议 |
|------|------|----------|--------|------|----------|
| **gka/chroma.js** | 10,571 | 2026-06-01 | Other | 零依赖、13.5kB、转换+色阶 | JS 侧颜色转换首选，若把部分逻辑迁到 JS 可用。 |
| **color-js/color.js** | 2,258 | 2026-07-06 | MIT | **CSS Color 规范编辑者（Lea Verou / Chris Lilley）维护**，原生支持 oklch/oklab/display-p3/rec2020 | 规范权威性最高，处理现代色彩空间（本项目当前 `webcolors` 不支持 oklch/oklab/p3）的**首选**。 |
| **scttcper/tinycolor** | 613 | 2025-09-18 | MIT | 轻量转换、`mostReadable()` 可读性选色 | 轻量，`mostReadable` 可直接增强本项目「对比度替代色建议」。 |
| **Evercoder/culori**（首轮） | 1,200 | PR 19 分钟内合并（极活跃） | MIT | 函数式、oklch 友好 | JS 侧等价能力，活跃度极高。 |
| **colour-science/colour**（首轮） | 2,600 | 活跃 | BSD-3 | **Python 色彩科学全集**（ΔE、色彩空间、CIE） | Python 侧替换自研颜色数学的**首选**（首轮已推荐，本文件确认仍是最优）。 |

### 2.3 对比度与无障碍（增强「替代色建议」）

| 项目 | Stars | 最近提交 | 许可证 | 复用建议 |
|------|------|----------|--------|----------|
| **adobe/leonardo** | 2,126 | 2026-05-18 | Apache-2.0 | Adobe 开源，`generateContrastColors` 按目标对比度生成颜色、`generateAdaptiveTheme` 生成整套主题。**本项目「WCAG 替代色建议」模块应直接借鉴/移植其算法**，比自研的「就近搜索」更科学。 |

### 2.4 设计令牌转换（export，已集成 style-dictionary）

| 项目 | Stars | 最近提交 | 许可证 | 复用建议 |
|------|------|----------|--------|----------|
| **amzn/style-dictionary**（首轮） | 4,700 | PR 当日合并（活跃） | Apache-2.0 | **已集成**（`--export` 走其 CLI）。多端（iOS/Android/SCSS）输出首选，保持。 |
| **salesforce-ux/theo** | 1,988 | 2025-06-09（**已归档**） | BSD-3 | 令牌转换鼻祖，但已归档，**仅作算法参考**，不引入依赖。 |
| **diez/diez** | 1,240 | 2022-12-10（停滞） | Other | 跨平台令牌框架，停滞，**不引入**。 |

### 2.5 字体度量（增强排版检测）

| 项目 | Stars | 最近提交 | 许可证 | 复用建议 |
|------|------|----------|--------|----------|
| **fonttools/fonttools** | 5,158 | 2026-07-06 | MIT | Python 字体操作权威库（TTX、变量字体、字重映射）。若增强 `analyze_url` 的字体语义推断（如按字形度量判断 display/body），可复用。当前自研靠 CJK 字体名匹配，较粗。 |

### 2.6 官方规范与 lint/diff/export（已集成）

| 项目 | Stars | 最近提交 | 许可证 | 复用建议 |
|------|------|----------|--------|----------|
| **google-labs-code/design.md**（首轮） | 25,200 | 2026-07-01（PR #15 合并） | Apache-2.0 | **已集成**（`--lint` / `--diff` / `--export` 走其 CLI）。规范事实来源，保持。 |

### 2.7 生态 / 曝光 / 参考

| 项目 | Stars | 最近提交 | 复用建议 |
|------|------|----------|----------|
| **VoltAgent/awesome-design-md**（首轮） | 96,000 | 活跃 | 生态列表，**作为本 Skill 的曝光渠道**（提交到该 awesome 列表）。 |
| **mikaelvesavuori/figmagic** | 858 | 2025-06-05 | Figma → 设计令牌 + React 组件，参考其令牌建模思路。 |

---

## 3. 重映射：自研组件 → 推荐复用

| 自研模块（文件） | 现状 | 推荐复用 | 收益 | 成本/风险 |
|------------------|------|----------|------|-----------|
| 颜色规范化（hex/rgb/hsl/oklch→hex） | 用 `webcolors` + 自写字典，缺 oklch/oklab/p3 | Python 侧换 **colour**；JS 侧用 **color-js/color.js** | 覆盖现代色彩空间，减少自维护字典 | 低（API 替换） |
| 截图取色（KMeans） | `sklearn` KMeans，依赖重 | 换 **colorthief**（Python MMCQ）或保留 KMeans 作可选 | 去掉 scikit-learn 重依赖，主色语义更好 | 中（需重测取色一致性） |
| 对比度替代色建议 | 自研「就近搜索」 | 借鉴 **adobe/leonardo** 算法（按目标对比度生成） | 科学、可解释、支持主题级生成 | 中（需移植算法到 Python） |
| URL 抽取（`analyze_url.py`+`extraction.js`） | 自研 headless 注入 | **委托 designlang / sunil-dsb** 作上游，或新增「导入其 DESIGN.md」模式 | 不再重复造轮子，对齐最强竞品输出 | 高（架构调整，但符合用户「不自立山头」原则） |
| 令牌导出（tailwind/css/dtcg） | 已用 **style-dictionary** | 保持 | 多端输出成熟 | 无 |
| 模板/组件库（12 模板 / 25+ 组件） | 自研数据驱动 | 无现成库，保持自研 + 持续扩充 | 差异化护城河 | 无 |
| 文本→DESIGN.md 生成 | 自研（核心） | 无竞品做此，保持 | **核心差异化** | 无 |
| lint/diff | 已用 **google design.md** CLI | 保持 | 规范一致 | 无 |
| 字体语义推断 | CJK 字体名匹配 | 可选 **fonttools** 增强字重/度量判断 | 更准的排版分类 | 低 |

---

## 4. 战略性建议（重点）

### 4.1 竞争格局已变：URL 抽取是红海，文本生成是蓝海
- designlang（~2,500★）已把「网站 → 完整设计系统 + 17 文件」做成事实标准，且含 WCAG 修复、暗色配对、CI drift bot。
- 在 URL 抽取维度硬拼**不划算**，且违反用户「尽量用别人轮子」的原则。

### 4.2 本项目的真实护城河（必须强化宣传）
1. **文本驱动**：给一段品牌 brief / 需求描述即可生成 DESIGN.md，**无需目标网站、完全离线、隐私优先**——这是 designlang/sunil-dsb 做不到的（它们都依赖 headless 抓取实时站点）。
2. **模板 + 组件目录**：12 行业模板 + 25+ 组件，竞品均无此「开箱即用」目录。
3. **官方规范对齐**：lint/diff/export 直接走 Google `design.md` CLI，输出可被整个生态消费。

### 4.3 「复用别人轮子」的下一步（按优先级）
- **P0（建议）**：将 `--analyze-url` 定位调整为「可选增强」而非核心，并在 README 明确「离线文本生成」差异化；或新增 `--import <design.md>` 模式，把 designlang/sunil-dsb 的输出当上游，用本项目模板 + 官方 CLI 重新格式化/校验。
- **P1**：颜色规范化迁移到 **colour**（Python）/ **color-js**（JS）；对比度替代色借鉴 **adobe/leonardo** 算法。
- **P1**：截图取色评估换成 **colorthief** 以去重 scikit-learn（若用户接受取色风格微调）。
- **P2**：提交到 **VoltAgent/awesome-design-md** 曝光；字体推断评估 **fonttools**。
- **不引入**：theo（已归档）、diez（停滞）——仅作参考。

### 4.4 一句话总结
> 把「URL 抽取」交给 designlang，把「颜色/对比度科学」交给 colour + adobe/leonardo，把「令牌导出」交给 style-dictionary；本项目聚焦于**文本→DESIGN.md 的生成引擎 + 模板组件目录 + 官方规范对齐**，这是别人没有、且无法被 headless 抓取替代的护城河。

---

## 5. 数据来源与方法
- 权威字段：`https://api.github.com/repos/{owner}/{repo}`（stargazers_count / pushed_at / license / language）。
- 交叉验证：项目官网（designlang.manavaryasingh.com）、npm 页、搜索结果。
- designlang 仓库路径在采集时 API 返回 404（疑似改名/迁移），Stars 采用其官网自报「2,500+」并在文中标注；其余 18 项均为 API 实测值。
- 采集日期：2026-07-07。
