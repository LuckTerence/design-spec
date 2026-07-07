# design-spec 上线前审查报告

- **审查日期**：2026-07-07
- **审查范围**：`/Users/terencesai/Desktop/vibecoding/github/skill/design-spec`（含 `scripts/`、`new/` 上传包、`SKILL.md`、`README.md`、`references/`）
- **审查维度**：① 上线前测试 ② GitHub 类似项目调研 ③ 架构与设计审查

---

## 一、上线前测试

### 1.1 测试环境与方法论

**测试环境**：Python 3.13.12 虚拟环境（依赖 `webcolors` / `pillow` / `numpy` / `scikit-learn` 均就绪）；`node` / `npx` / `agent-browser` 可用；`@google/design.md` 官方 CLI 已可解析。

**测试方法**：编写自动化测试驱动（`subprocess` 调用真实脚本），覆盖 **功能测试、边界条件测试、异常处理测试** 三类，共 **42 项断言**。每个用例校验返回码、产物文件存在性、关键内容字符串、以及降级/告警行为。

### 1.2 测试结果汇总

| 测试类别 | 用例数 | 通过 | 失败 | 结论 |
|----------|--------|------|------|------|
| 功能测试 | 24 | 24 | 0 | 全部通过 |
| 边界条件 | 13 | 13 | 0 | 全部通过 |
| 异常处理 | 5 | 5 | 0 | 全部通过 |
| **合计** | **42** | **42** | **0** | **零崩溃** |

### 1.3 功能测试覆盖点

- **基础生成**：`--name` + `--primary` 正常产出 `DESIGN.md`，含 20+ 颜色令牌、12 级字体、25+ 组件定义。
- **12 个行业模板**：`enterprise` / `ecommerce` / `finance` / `creative` / `healthcare` / `education` / `gaming` / `food-beverage` / `real-estate` / `travel` / `social-media` / `developer-tools` 全部生成成功。
- **深色主题自适应**：`--background "#0D1117" --text ""` 正确识别为深色主题，文字色自动取浅色 `#e8eaed`，surface 自动提亮。
- **迭代修改与派生色同步**：`--modify` 修改主色后，`primary-hover` / `primary-active` / `primary-light` 等派生色自动重算。
- **`--spacing-base` 透传**：修改模式下间距基准正确同步。
- **色板可视化**：`--visualize` 产出合法 SVG（`<?xml` 根节点校验通过）。
- **代码导出**：`--export tailwind/css/dtcg` 三个格式均产出文件，且确认优先走官方 `@google/design.md` CLI（`cli=True`）。
- **lint / diff**：调用官方 CLI，缺失文件时优雅报 `rc=1` 并提示安装方式。
- **截图分析**：构造测试图后 `--analyze` 产出 `DESIGN.md` + `_analysis.json`，无崩溃。

### 1.4 边界与异常验证

| 场景 | 预期行为 | 实测 |
|------|----------|------|
| 输出路径含 `..` | 拒绝（`rc=1`） | 通过 |
| 缺 `--name` | 拒绝（`rc=1`） | 通过 |
| 非法颜色值 | 回退默认值 + 告警（`rc=0`） | 通过 |
| `--spacing-base 100 / -5` | 钳制到 `[2,16]`（`xs` 分别为 `16px` / `2px`） | 通过 |
| `--colors 1 / 50`（截图脚本） | 拒绝（`rc!=0`） | 通过 |
| 缺失的输入文件（analyze/lint/diff/modify） | 优雅报错 | 通过 |
| `--modify` 目标无 YAML 前缀 | 优雅报错（`rc=1`） | 通过 |
| `--analyze-url ftp://...` | 非法 scheme 优雅拒绝 | 通过 |
| 名称含换行/YAML 控制字符 | 注入被中和（转空格） | 通过 |
| 中文品牌名 | 自动匹配中文字体（PingFang SC / Noto Sans SC） | 通过 |

### 1.5 崩溃风险与未覆盖路径

- **实际崩溃**：42/42 全通过，**未发现崩溃路径**。
- **高依赖外部环境的路径（本次未做真实联网验证）**：`--analyze-url` 依赖 `agent-browser` + 真实浏览器 + 网络，离线环境无法端到端验证；已验证非法 scheme 优雅拒绝与子进程异常捕获。
- **设计性限制（非缺陷）**：`--lint` / `--diff` 仅依赖官方 CLI，无本地兜底（README 已说明）；`--export` 有本地 fallback。

### 1.6 测试期发现并已修复的问题

| 问题 | 严重度 | 处置 |
|------|--------|------|
| `new/` 上传包与 `scripts/` 根目录不同步，且 `new/` 中 `--modify` 不带 `--output` 会误写到 `DESIGN.md` 而非原地覆盖 | **高（发布阻塞）** | 已同步 `new/` 至根目录并清理 `__pycache__` |
| 组件说明文案拼写错误 `surfate` | 低 | 已改为 `surface` |
| 仓库中存在 `__pycache__` / `*.pyc` 散落文件 | 低 | 已清理（`.gitignore` 已忽略，但磁盘上不应残留） |

---

## 二、GitHub 类似项目调研

数据来源：GitHub REST API（`api.github.com/repos/...`），检索于 2026-07-07；规范描述来自 `google-labs-code/design.md` 官方仓库与规范页。

### 2.1 可比项目横向对比

| 项目 | Stars | 协议 | 最近提交 | 维护活跃度 | 可复用模块 / 库 | 与本项目关系 |
|------|-------|------|----------|------------|----------------|--------------|
| **google-labs-code/design.md** | 25,185 | Apache-2.0 | 2026-07-01 | 极高（Google Labs 官方） | `@google/design.md` CLI：`lint` / `diff` / `export`；DESIGN.md 规范本体 | **已集成**（lint/diff/export 直接调用官方 CLI，符合“不重复造轮子”原则） |
| **style-dictionary** | 4,722 | Apache-2.0 | 2026-06-21 | 高 | 跨平台设计令牌构建引擎（→ iOS / Android / SCSS / 等多端） | 可增强 `--export`，补充官方 CLI fallback 不支持的多端输出 |
| **colour-science/colour** | 2,617 | BSD-3-Clause | 2026-06-29 | 高 | Python 色彩科学库：`oklab` / `oklch` / `hwb` 转换、Delta-E、WCAG 对比度 | 可替换本项目手写的三处颜色/对比度数学，提升色彩空间正确性 |
| **Evercoder/culori** | 1,207 | MIT | 2026-07-02 | 高 | JavaScript 色彩库（CSS Color 4 全空间） | 若浏览器侧提取/分析未来迁 Node，可作正确色彩数学参考 |
| **jasonhnd/design-md-generator** | 2 | MIT | 2026-04-19 | 停滞 | URL→DESIGN.md 生成器（Playwright 提取计算样式） | 直接竞品，但成熟度低；其功能方向已被本项目 `--analyze-url` 覆盖 |
| **VoltAgent/awesome-design-md** | 96,257 | MIT | 2026-06-16 | 极高 | DESIGN.md 生态精选列表（非工具库） | 非代码复用对象，但可作为本项目示例/推广的曝光渠道 |

### 2.2 各项目优势与可复用点

- **google-labs-code/design.md（上游规范 + 官方 CLI）**：作为 DESIGN.md 格式的事实标准，其 CLI 的 `lint` / `diff` / `export` 是本项目“不自立山头”策略的基石。本项目已正确复用，**该方向无需变更**。
- **style-dictionary**：当前 `--export` 的本地 fallback 仅覆盖 `tailwind` / `css` / `dtcg`；`style-dictionary` 可将同一份令牌编译到 iOS / Android / SCSS 等更多平台，是增强导出能力的成熟轮子。
- **colour-science/colour**：本项目在 `generate_design_spec.py`、`analyze_screenshot.py`、`analyze_url.py` 三处各自手写了 `oklch` / `oklab` / `hwb` 转换与 WCAG 对比度计算。`colour` 库提供经过验证的色彩空间转换与色差公式，可消除重复代码并提升边界正确性（如色域映射）。
- **Evercoder/culori**：JS 侧等价能力，主要价值在于为 `extraction.js` / `analyze_url.py` 未来的 Node 化提供参考实现。
- **jasonhnd/design-md-generator**：竞品参照，确认“URL 反向提取 DESIGN.md”是合理赛道；但其 2 Stars、近三个月无提交，不足以作为复用来源。
- **VoltAgent/awesome-design-md**：96K Stars 主要为生态聚合列表（非单一工具），适合作为本项目在上线后提交示例、获取曝光的渠道，与既有小红书推广形成互补。

### 2.3 调研结论

本项目“文本/截图/URL → DESIGN.md”的生成定位在同赛道中具备差异化优势（上游官方 CLI 仅做 lint/diff/export，不做正向生成）。复用策略正确：**核心校验/导出已绑定官方 CLI**；下一步建议把**颜色数学**与**多端导出**两个自建环节分别向 `colour` 与 `style-dictionary` 靠拢，进一步降低维护面。

---

## 三、架构与设计审查

### 3.1 安全性

| 检查项 | 结论 |
|--------|------|
| 路径遍历（`..` 拒绝） | 达标（边界测试 B1 通过） |
| YAML 注入（换行/控制字符/引号转义） | 达标（`escape_yaml` 覆盖；C3 通过） |
| 颜色输入校验与回退 | 达标（支持 hex/rgb/hsl/oklch/oklab/hwb/命名色，`transparent`；非法值回退+告警） |
| 子进程调用（`subprocess` 列表参数，无 `shell=True`） | 达标（无命令注入风险） |
| URL 校验（仅 `http/https`） | 达标（C2 通过） |
| 原子写入（临时文件 + `os.replace`） | 达标（生成中断不损坏目标文件） |

**残余风险（低）**：截图输入无显式体积上限（已由 `thumbnail(2000,2000)` 兜底，内存可控）；`--analyze-url` 会访问用户提供的任意 URL（功能固有，已通过 README 提示）。

### 3.2 性能

- 截图分析：`thumbnail` 降采样 + 网格采样 + `MiniBatchKMeans`，无显著瓶颈；KMeans 失败路径有频率兜底。
- 正向生成：纯字符串拼接，毫秒级。
- 导出/校验：委托外部 CLI，耗时由 CLI 与网络决定（已设超时）。
- **结论**：无性能阻塞点。

### 3.3 可扩展性

- **模板与组件硬编码于代码内**：12 个模板存于 `TEMPLATES` 字典，25+ 组件以三引号字符串内嵌于 `generate_yaml_frontmatter`。新增模板/组件需改代码，扩展成本较高。
- **颜色/对比度数学三处重复**：`generate_design_spec.py`、`analyze_screenshot.py`、`analyze_url.py` 各自实现 `oklch` / `oklab` / `hwb` 与 WCAG 计算，维护一致性风险。
- **无插件/配置驱动机制**：对 Skill 场景可接受，但数据驱动化可显著降低后续扩展门槛。

### 3.4 代码规范

- **仓库内缺少自动化测试**：本次 42 项测试为临时驱动，未沉淀为 `pytest` 用例，后续改动易回归。
- **少量不可达代码**：`--tone` 的 CLI 层回退（`tone = args.tone if args.tone in VALID_TONES else "专业"`）因 `argparse` 的 `choices` 在 CLI 路径已拦截非法值，仅 `--modify --set tone=...` 路径可达（功能正确，属冗余）。
- **文档/产物曾不同步**：`new/` 上传包一度滞后于根目录（已修复）；建议将“上传包与根目录一致性”纳入提交检查。

### 3.5 优化建议与优先级

| 优先级 | 优化项 | 说明 | 工作量 |
|--------|--------|------|--------|
| **P0（已修复）** | `new/` 上传包同步 + 清理 `__pycache__` + 修正 `surfate` 拼写 | 发布阻塞项，已处置 | 低 |
| **P0** | 提交前确认 `root` 与 `new/` 字节一致 | 避免再次出现上传包滞后 | 低 |
| **P1** | 沉淀 `pytest` 冒烟测试 | 覆盖 12 模板 + `--modify` 派生同步 + 边界（spacing-base / colors / 路径遍历），防回归 | 中 |
| **P1** | 颜色/对比度数学集中化或采用 `colour-science/colour` | 消除三处重复，提升 `oklch`/`oklab`/`hwb` 边界正确性 | 中 |
| **P1** | 模板/组件数据驱动（外部 YAML） | 扩展无需改代码，降低维护面 | 中 |
| **P2** | 评估 `style-dictionary` 增强 `--export` | 补充 iOS/Android/SCSS 多端输出 | 中 |
| **P2** | `analyze_url` 增加重试/限流与超时文档 | 提升联网采样的健壮性说明 | 低 |
| **P2** | 增加 GitHub Actions CI | push 时跑 `--check` + 冒烟测试，守住质量底线 | 低 |

---

## 四、结论与上线清单

**功能性**：42/42 自动化测试通过，零崩溃，功能、边界、异常路径均表现稳健。

**安全性**：路径遍历、YAML 注入、颜色校验、子进程安全、原子写入均达标。

**调研结论**：复用策略正确（lint/diff/export 绑定官方 CLI）；下一步建议把颜色数学与多端导出分别向 `colour` 与 `style-dictionary` 靠拢。

**发布阻塞项（本次已修复）**：`new/` 上传包与根目录不同步（含 `--modify` 原地覆盖 bug）、`surfate` 拼写错误、`__pycache__` 残留。

**上线前请确认**：

1. `root` 与 `new/` 文件现已一致，可直接用于 RedSkill / GitHub 上传。
2. 将本次审查沉淀的 `pytest` 冒烟测试纳入仓库，防止后续回归。
3. 若计划扩展模板/组件，优先采用外部 YAML 数据驱动方案。
4. README 已说明 `--lint`/`--diff` 依赖官方 CLI，安装说明完整，无需补充。

---

**数据来源**：GitHub REST API（`api.github.com/repos/{owner}/{repo}`），检索于 2026-07-07；DESIGN.md 规范描述来自 `google-labs-code/design.md` 官方仓库与规范页（`stitch.withgoogle.com/docs/design-md/specification`）。
