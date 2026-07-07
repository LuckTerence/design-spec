# design-spec 同赛道 15 个 GitHub 项目深度调研

> 执行时间：2026-07-07 | 数据来源：GitHub REST API + 项目 README + 源码快照  
> 检索维度：**复用价值**（能否借用其代码/库） + **功能对比**（对方有而我们没有的亮点） + **护城河确认**（我们有而对方没有的差异化）

---

## 一、项目总览

| # | 项目 | Stars | 语言 | 最后推送 | 与本项目关系 |
|---|------|-------|------|---------|-------------|
| 1 | **google-labs-code/design.md** | 25,200 | TS/CLI | 2026-07 | 规范标准 + CLI 上游（lint/diff/export 已集成） |
| 2 | **nextlevelbuilder/ui-ux-pro-max-skill** | 101,862 | Python/CSV | 2026-07-06 | **最强参考**：AI 设计系统推理引擎，161 条行业规则 |
| 3 | **VoltAgent/awesome-design-md** | 96,000 | Markdown | 活跃 | 生态列表，本 Skill 的曝光渠道 |
| 4 | **amzn/style-dictionary** | 4,700 | JS | 活跃 | 令牌导出上游（已集成） |
| 5 | **Manavarya09/design-extract (designlang)** | 2,500+ | TS | 2026-07 | URL→设计系统（已委托 `--import`） |
| 6 | **lukasoppermann/design-tokens** | 1,113 | TS | 2026-02 | Figma→令牌导出插件 |
| 7 | **no7z/design-pact** | 1 | TS | 2026-07-06 | **最接近的竞品**：palette→design.md 契约 |
| 8 | **gitstq/designkit-cli** | 0 | Python | 2026-06 | 0-dep Python 预设主题生成器 |
| 9 | **gitstq/DesignTokenX** | 0 | Python | 2026-05 | 网站→DESIGN.md Python 提取器 |
| 10 | **nomoarai/design-tokens-forge** | 0 | Python | 2026-06 | brand.json→CSS/JSON/SD CLI |
| 11 | **Aina483/StyleForge** | 0 | TS/Node | 2026-06 | AI(Gemini) 驱动设计系统生成器 |
| 12 | **sunil-dsb/design.md** | 50 | TS | 2026-05 | 网站→DESIGN.md 提取 |
| 13 | **KodeKenobi/DesignTokenExtractor** | 0 | JS | 2026-06 | Chrome 扩展，实时编辑+导出令牌 |
| 14 | **Easy-Hexford/design-md-generator** | 2 | JS | 2026-04 | 网站/本地源码→DESIGN.md |
| 15 | **a692570/design-extractor** | 1 | JS | 2026-04 | Chrome 扩展，逆向工程设计系统 |

---

## 二、逐项目详细分析

### 1. `google-labs-code/design.md` — 规范标准（已集成）

| 维度 | 评估 |
|------|------|
| **复用** | ✅ 已集成。`--lint` / `--diff` / `--export` 优先调用其 CLI |
| **对方有而我们没有** | 完整的规范校验生态（ast 解析、版本 diff、多格式导出） |
| **我们建议** | 保持集成；考虑添加 `--validate` 命令包装其 `design.md lint` |

### 2. `nextlevelbuilder/ui-ux-pro-max-skill` — 最强参考 ⭐

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（其核心是 CSV 数据 + BM25 排序推理，非程序库） |
| **对方有而我们没有** | **① 161 条行业推理规则**：8 大类产品类型 × 匹配色板/风格/字体/反模式（我们仅 12 模板，且无反模式）<br>**② Master + Overrides 分层**：全局 MASTER.md + 页面级别 page.md 覆盖<br>**③ 反模式列表**：每个行业明确"不能做什么"（如金融避免紫色渐变）<br>**④ 161 色板 × 57 字体搭配 × 67 UI 风格**：结构化的行业设计知识库 |
| **我们建议学习** | **P1**：扩充模板数据量（从 12 扩到 50+），每个模板增加反模式列表<br>**P1**：引入分层设计系统（`--master` + `--page`），支持多页面派生 |
| **我们**的护城河 | 对方生成的是**描述性规则**（AI prompt），我们生成的是**精确的设计令牌 + DESIGN.md 文件**，可被任何工具消费 |

### 3. `no7z/design-pact` — 最接近的直接竞品 ⭐

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（TypeScript，单页 Web 应用） |
| **对方有而我们没有** | **① `check` 命令**：扫描项目源代码，审计 hex/rgb 颜色字面量是否偏离 DESIGN.md 规范，报告文件和行号——**这是 killer feature**<br>**② `import` 遗留项目适配**：扫描现有代码库自动推导设计.md（Tailwind 配置/CSS 变量/颜色使用）<br>**③ Studio 可视化编辑器**：OKLCH 色轮 + 实时 Mockup + 对比度滑动条<br>**④ culori** 替代 coloraide 做 oklch 色相推移 |
| **我们建议学习** | **P0**：`check` 命令——审计项目源代码与 DESIGN.md 的一致性，这是我们最缺失的工程能力<br>**P1**：`import` 遗留项目适配——扫描 CSS/Tailwind 配置推断设计规范 |
| **我们**的护城河 | 对方需要 Node.js 环境 + 可视化编辑器；我们纯 Python CLI，无前端依赖，WorkBuddy Skill 内嵌调用体验高于独立 Web 工具 |

### 4. `gitstq/designkit-cli` — 最近的 Python 同行

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（纯 Python 但 0 stars，仅 1 commit） |
| **对方有而我们没有** | **① 交互式 TUI 预览**：Rich-powered 终端预览主题色板<br>**② 7 预设主题**：minimal/brutalist/warm/neon/corporate/playful/nature<br>**③ AI Prompt 生成**：输出 GLM-5.1/GPT/Claude 可直接使用的设计系统 prompt |
| **我们建议学习** | **P2**：参考其 palette 命令的 50-950 色阶生成算法（从单色生成 Tailwind 完整色阶）<br>**P2**：参考其 AI prompt 输出格式，让本项目也能输出"AI 可直接消费"的 design system prompt |
| **我们**的护城河 | 我们有 12 模板 + 25+ 组件 + DESIGN.md 标准输出，对方仅有 7 预设 + 无组件定义 |

### 5. `gitstq/DesignTokenX` — Python 网站→DESIGN.md

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（0 依赖 Python 但 0 stars，仅 1 commit，需 Playwright） |
| **对方有而我们没有** | **① 置信度评分**：每个 tokens 有 HIGH/MEDIUM/LOW 信心度<br>**② 框架自动检测**：识别 React/Vue/Tailwind<br>**③ 多格式同时输出**：一次提取输出 DESIGN.md + JSON + DTCG |
| **我们建议学习** | **P2**：`--import` 时增加置信度标注，帮助用户判断导入质量 |
| **我们**的护城河 | 对方只能从**已有网站**提取，不能从**文本描述**生成；我们有 12 模板，对方没有模板概念 |

### 6. `nomoarai/design-tokens-forge` — brand.json→设计令牌

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（纯标准库 Python，但仅 2 commits，0 依赖的代价是功能极简） |
| **对方有而我们没有** | **① brand.json 作为单一事实来源**：一个 JSON 文件定义品牌全部设计决策<br>**② 零依赖**：纯 Python 标准库，不装任何 pip 包也能跑 |
| **我们建议学习** | **P2**：新增 `--from-json` 模式，允许用户传入 `brand.json` 作为输入（适配方已经用 JSON 管理品牌色的用户） |
| **我们**的护城河 | 对方仅做"扁平属性→CSS/JSON 映射"的纯格式转换，无色彩派生、无 WCAG 对比度、无模板、无 DESIGN.md 输出 |

### 7. `Aina483/StyleForge` — AI 驱动设计系统

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（Node.js + React + Gemini API） |
| **对方有而我们没有** | **① AI 推理生成**：用 Gemini 2.0 Flash 从品牌输入推理完整令牌集<br>**② 实时组件预览**：React 组件实时展示令牌效果<br>**③ Redux undo/redo**：编辑令牌可撤销/重做 |
| **我们建议学习** | 其"AI 推理"方向与我们的"确定性算法"方向不同——我们不依赖 AI 推理，更适合离线场景。保留此定位不动 |
| **我们**的护城河 | 对方依赖 Gemini API（需联网 + API Key），无法离线运行；我们完全离线 |

### 8. `sunil-dsb/design.md` — 网站→DESIGN.md

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（TS/Node，需 headless 浏览器） |
| **对方有而我们没有** | **① 更丰富的 UI 偏好检测**：暗色/亮色、圆角风格、动画偏好 |
| **我们建议学习** | 信息已在 REUSABLE_LIBS.md 覆盖 |

### 9. `KodeKenobi/DesignTokenExtractor` — Chrome 扩展

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（Chrome 扩展，非 CLI 工具） |
| **对方有而我们没有** | **① 实时页面编辑器**：点选页面元素即可实时编辑样式并生效<br>**② 使用频率统计**：每个间距值/颜色值统计使用次数，反映其在设计系统中的重要程度<br>**③ 智能捕获 + Shadow DOM**：一键捕获页面设计，用 Shadow DOM 防止样式冲突 |
| **我们建议学习** | **P2**：`--analyze screenshot` 输出增加频率/置信度信息 |

### 10. `Easy-Hexford/design-md-generator` — 网站/源码→DESIGN.md

| 维度 | 评估 |
|------|------|
| **复用** | 不可直接复用（2 stars，无许可证，一天停止推送） |
| **对方有而我们没有** | **① 本地源码提取**：不经过浏览器，直接从 CSS/SCSS/HTML/JSX/TSX/Vue 文件提取令牌——这是我们没有的"本地项目→设计规范"能力 |
| **我们建议学习** | **P1**：新增 `--import-local <project-dir>` 模式，从本地项目目录提取 CSS 变量/颜色/tailwind.config 推断设计规范 |

### 11-15. 其他参考项目

| 项目 | 关键启示 |
|------|---------|
| **lukasoppermann/design-tokens** (1,113★) | Figma ↔ GitHub 令牌流水线架构不直接相关，但其 **W3C DTCG 格式导出** 是我们应该全面支持的 |
| **a692570/design-extractor** (1★) | Chrome 扩展，功能同 KodeKenobi，**不支持** |
| **jasonhnd/design-md-generator** (2★) | 已确定停滞，**无价值** |
| **amzn/style-dictionary** (4,700★) | 已集成，考虑进一步提升集成度（确保 npx style-dictionary 在 `--export` 时可用） |
| **VoltAgent/awesome-design-md** (96K★) | 我们应提交到该列表作为曝光渠道 |

---

## 三、可复用性总结

```
┌──────────────────────────────────────────────────────────────────┐
│ 15 个项目中，可直接复用（作为 pip/npm 依赖引入）的：             │
│                                                                  │
│  ✅ google-labs-code/design.md  → 已集成（lint/diff/export）     │
│  ✅ amzn/style-dictionary       → 已集成（令牌导出）             │
│  ✅ Manavarya09/design-extract  → 已委托（--import 模式）        │
│                                                                  │
│ 不可直接复用（生态定位不同 / 太新太小 / 语言不兼容）：            │
│  ❌ no7z/design-pact    (TS/Web应用)                              │
│  ❌ designkit-cli       (0★/1 commit)                             │
│  ❌ DesignTokenX        (0★/1 commit)                             │
│  ❌ design-tokens-forge (0★/2 commits)                            │
│  ❌ StyleForge          (需 Gemini API)                           │
│  ❌ ui-ux-pro-max-skill (101K★ 但为推理引擎，非库)                │
│  ❌ 其余 Chrome 扩展    (不可内嵌)                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 四、值得学习的 5 个功能（建议按优先级实现）

| 优先级 | 功能 | 参考项目 | 估算工作量 | 价值 |
|--------|------|---------|-----------|------|
| **P0** | **`check` 源代码审计**：扫描项目源码的 hex/rgb 颜色字面量，对比 DESIGN.md 报告偏离 | no7z/design-pact | 中等（~80 行） | 让 DESIGN.md 从"文档"变成"可执行契约"，直接在 CI 中校验代码是否跑偏 |
| **P1** | **`--import-local` 本地项目提取**：扫描 CSS 变量 / tailwind.config / 颜色使用，自动推导 DESIGN.md 草稿 | design-pact / Easy-Hexford | 中等（~120 行） | 解决"已有项目如何快速接入"的痛点 |
| **P1** | **扩模板至 50+**：参考 ui-ux-pro-max-skill 的 161 行业规则，增加更多行业色板 + 反模式描述 | ui-ux-pro-max-skill | 数据工作（两天） | 从 12 模板到 50+ 覆盖更多行业，大幅提升开箱即用体验 |
| **P1** | **Master + Overrides 分层**：支持 `--master` 定义全局规范 + `--page` 定义页面级别覆盖 | ui-ux-pro-max-skill | 中等（~150 行） | 适配大型项目多页面不同子风格的需求 |
| **P2** | **置信度评分**：`--import` 和 `--analyze` 输出加置信度标签 | DesignTokenX | 低（~30 行） | 帮助用户判断导入质量 |

---

## 五、护城河确认

对比 15 个项目后，本项目**不可被替代**的差异化：

| 能力 | design-spec | design-pact | designkit-cli | ui-ux-pro-max | designlang |
|------|------------|-------------|---------------|---------------|------------|
| 文本→DESIGN.md | ✅ | ❌ | ❌ | ❌ | ❌ |
| 12 模板+25+组件 | ✅ | ❌ | 7 预设 | 行业规则（无输出文件） | ❌ |
| 离线运行 | ✅ | ✅ | ✅ | ❌（下载 CSV） | ❌（需浏览器） |
| Python CLI | ✅ | ❌ TS | ✅ | ✅ | ❌ TS |
| WorkBuddy Skill | ✅ | ❌ | ❌ | ✅ | ❌ |
| DESIGN.md 输出 | ✅ | ✅ | ❌ | ❌ | ✅ |
| check 审计 | ❌ | ✅ | ❌ | ❌ | ❌ |
| WCAG 对比度 | ✅ | ✅ | ❌ | ❌ | ✅ |
| 截图取色 | ✅ | ❌ | ❌ | ❌ | ❌ |

**一句话定位**：我们是唯一一个**纯离线 Python CLI + 文本→DESIGN.md + 12 模板+25 组件 + 截图分析**的全栈设计规范生成器。

---

## 六、数据来源

- GitHub REST API：`api.github.com/repos/{owner}/{repo}`（stargazers_count/pushed_at/language）
- 项目 README / 源码：逐仓库读取分析
- 采集日期：2026-07-07
