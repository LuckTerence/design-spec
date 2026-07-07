# design-spec 上线前综合审查报告（扩展版 V2）

- **审查日期**：2026-07-07
- **审查范围**：`/Users/terencesai/Desktop/vibecoding/github/skill/design-spec`（`scripts/`、`new/` 上传包、`SKILL.md`、`README.md`、`references/`）
- **审查维度**：① 上线前测试（功能 / 边界 / 异常 / 性能 / 安全 / 覆盖率 / 风险等级）② GitHub 同类项目调研（含文档完善度、提交活跃度、Issue 响应、集成方式）③ 架构与设计审查（安全 / 性能 / 可扩展性 / 代码规范 / 可维护性 / 数据库设计 / API 设计规范 / 优先级与工作量）④ 上线 Checklist
- **数据来源**：GitHub REST API（`api.github.com/repos/{owner}/{repo}` 与 `/issues`、`/readme`），检索于 2026-07-07；DESIGN.md 规范描述来自 `google-labs-code/design.md` 官方仓库。

> 本报告为 2026-07-07 初版 `PRELAUNCH_REVIEW.md` 的扩展。初版已覆盖功能 / 边界 / 异常三类 42 项测试与基础调研；本版新增**性能压测、内存、并发、安全压测、行覆盖率、风险等级清单、文档完善度、提交活跃度、Issue 响应、集成方式、数据库 / API 设计维度与上线 Checklist**，并将优化建议补全为带工作量估算的 P0/P1/P2 清单。

---

## 一、上线前测试审查

### 1.1 测试环境与方法论

**测试环境**：Python 3.13.12 虚拟环境（依赖 `webcolors 25.10.0` / `pillow 12.3.0` / `numpy 2.5.1` / `scikit-learn 1.9.0`）；`node` / `npx` / `agent-browser` 可用；`@google/design.md` 官方 CLI 可解析。

**方法论**：以 `coverage.py` 覆盖率采集为基础，编写 36 项断言的综合驱动，覆盖 **功能、边界、异常、性能、内存、并发、安全** 七类。性能用 `time.perf_counter` 取 3 次中位数；内存用 `tracemalloc` 取单次生成峰值；并发以**子进程隔离**（真实 CLI 并发）验证原子写；安全以超大输入、NUL 字节、符号链接、YAML 注入构造攻击样本。

### 1.2 测试结果汇总

| 测试类别 | 用例数 | 通过 | 失败 | 结论 |
|----------|--------|------|------|------|
| 功能（12 模板 / modify / visualize / export×3 / check / lint / diff / 截图 / URL-scheme） | 22 | 22 | 0 | 全部通过 |
| 边界（路径遍历 / 缺 name / 非法色 / spacing 钳制 / 截图 colors 区间） | 7 | 7 | 0 | 全部通过 |
| 异常与性能 / 内存 / 并发 / 安全 | 7 | 7 | 0 | 全部通过 |
| **合计** | **36** | **36** | **0** | **零崩溃** |

### 1.3 行覆盖率报告

以 `coverage run --source=scripts` 采集，结果如下：

| 模块 | 语句数 | 未覆盖 | 覆盖率 | 说明 |
|------|--------|--------|--------|------|
| **generate_design_spec.py**（核心引擎） | 875 | 271 | **69%** | 未覆盖主要为 `--analyze-url` 反推分支与少数深層回退 |
| **analyze_screenshot.py**（截图分析） | 264 | 50 | **81%** | 边界与异常分支部分未触发 |
| **analyze_url.py**（URL 反推） | 478 | 437 | **9%** | 强依赖 `agent-browser` + 真实浏览器 + 网络，离线无法端到端覆盖 |
| **合计** | 1617 | 758 | **53%** | 核心生成链路覆盖充足；URL 反推为已知覆盖盲区 |

**覆盖率盲区说明（已知事实）**：`analyze_url.py` 的 9% 源于其本体即"调用 `agent-browser` 抓取网页 → 抽取计算样式"。该路径在无浏览器 / 无网的 CI 中无法执行，属结构性限制而非代码缺陷。当前已通过非法 scheme 拒绝与子进程异常捕获覆盖其入口安全性。

### 1.4 性能压测

对 12 个行业模板各生成 3 次取中位数：

| 指标 | 数值 |
|------|------|
| 单模板生成耗时（中位数） | **0.53ms ~ 0.85ms** |
| 最慢模板（food-beverage / real-estate） | 0.85ms |
| 内存峰值（tracemalloc，单次生成） | **0.088 MB** |

**结论（已知事实 + 分析）**：正向生成纯字符串拼接，耗时与内存均为亚毫秒 / 亚兆级，**不存在性能瓶颈**。截图分析经 `thumbnail` 降采样 + `MiniBatchKMeans`，耗时由图像尺寸与聚类数决定，属可接受范围。

### 1.5 并发与原子性测试

| 场景 | 配置 | 结果 |
|------|------|------|
| 独立并发生成 | 8 个子进程并发写 8 个不同文件 | **8/8 成功**，产物均有效 |
| 同文件竞争写 | 6 个子进程并发写同一输出文件 | 最终文件含合法 YAML（`---` 成对），**未损坏** |

**结论（分析）**：脚本以 `tempfile` + `os.replace` 原子写，竞争写场景下后写者覆盖、无半截文件。CLI 以独立进程运行，天然无共享内存态，**并发安全**。

### 1.6 安全压测

| 攻击样本 | 预期 | 实测 |
|----------|------|------|
| 名称长度 **10,000 字符** | 正常生成不崩溃 | 通过 |
| 名称含 **NUL 字节**（`Bad\x00Name`） | 异常被捕获，不向上抛 | 通过 |
| 输出路径为**符号链接** | 正常写入，不越权 | 通过 |
| 名称含 **YAML 注入**（`evil\nhacked: true`） | 换行转空格 + 引号包裹，注入未成为独立 frontmatter 键 | 通过（frontmatter 仅含 `name: "evil hacked: true"`） |

### 1.7 风险等级清单

| 风险项 | 等级 | 证据 | 建议 |
|--------|------|------|------|
| `analyze_url.py` 覆盖率仅 9%（回归不可测） | **P1** | 1.3 节覆盖率表 | 增加 mock / CI 中启用 `agent-browser` 的集成测试 |
| 仓库无依赖锁定文件 | **P1** | 第四章 Checklist 实测 | 新增 `requirements.txt` 固定版本（本报告已落实） |
| 测试未沉淀进仓库 | **P1** | 初版 42 项 + 本版 36 项均在 `/tmp` | 提交 `tests/` 冒烟套件（本报告已落实） |
| 颜色 / 对比度数学三处重复 | **P1** | generate / screenshot / url 各写一份 | 集中化或采用 `colour-science/colour` |
| 模板 / 组件硬编码于代码 | **P1** | `TEMPLATES` 字典 + 三引号字符串 | 外部 YAML 数据驱动 |
| `--export` 多端能力不足 | **P2** | 仅 tailwind / css / dtcg | 评估 `style-dictionary` |
| 缺少稳定程序化 API | **P2** | 函数可导入但无公开契约 | 暴露 `generate(tokens) -> str` |
| 无 CI | **P2** | 无 `.github/workflows` | 加 GitHub Actions 跑冒烟测试 |

---

## 二、GitHub 同类项目调研（扩展）

数据来自 GitHub API，检索于 2026-07-07。表格按"**可复用价值**"排序。

| 项目 | Stars | 最近提交 | 文档完善度 | Issue 响应（API 实录） | 协议 | 集成方式 | 可复用模块 |
|------|-------|----------|------------|------------------------|------|----------|------------|
| **google-labs-code/design.md** | 25,198 | 2026-07-01 | README 12.4KB + 官方规范站 | 活跃：PR#152（07-06 开）、Issue#16（07-03 仍有讨论）、PR#15（07-01 维护者合并） | Apache-2.0 | `npx @google/design.md lint/diff/export` | **已集成**：lint/diff/export CLI 与 DESIGN.md 规范本体 |
| **amzn/style-dictionary** | 4,722 | 2026-06-21 | README 16.3KB + 文档站 | 活跃：PR#1701 / #1700 均于 06-21 由维护者合并 | Apache-2.0 | `npm i style-dictionary`（JS/TS API + 配置） | 跨平台令牌构建引擎（iOS/Android/SCSS/CSS…） |
| **colour-science/colour** | 2,617 | 2026-06-29 | README.rst 73KB（极完备）+ 文档站 | 中速：PR#1408（06-30 更新，4 评论）；部分外部 Issue 无人即时回应 | BSD-3-Clause | `pip install colour`（Python API） | `oklab`/`oklch`/`hwb` 转换、Delta-E、WCAG 对比度 |
| **Evercoder/culori** | 1,207 | 2026-07-02 | README 仅 1.3KB（详文档在 culorijs.org 站外） | 快但有选择：PR#271 维护者 19 分钟合并；Issue#269 23 分钟关闭；外部 PR#270 仍挂起 | MIT | `npm i culori`（JS API） | JS 侧 CSS Color 4 全空间数学 |
| **VoltAgent/awesome-design-md** | 96,283 | 2026-06-16 | 本身是精选列表（非工具文档） | 高 backlog（open_issues 298），列表型项目 | MIT | 不适用（非库） | **非代码复用**；作为本项目示例曝光渠道 |
| **jasonhnd/design-md-generator** | 2 | 2026-04-19（停滞） | 极小 | 无活动（open_issues 0，近 3 月无提交） | MIT | Playwright URL→DESIGN.md | **无复用价值**；其功能已被本项目 `--analyze-url` 覆盖 |

### 2.1 各项目优势与集成细节

- **google-labs-code/design.md（上游规范 + 官方 CLI）**：DESIGN.md 格式事实标准。其 CLI 的 `lint`/`diff`/`export` 是本项目"不自立山头"策略基石，**已正确复用，方向无需变更**。本项目差异化在于"文本 / 截图 / URL → DESIGN.md"正向生成，上游 CLI 不做此部分。
- **amzn/style-dictionary**：当前 `--export` 本地 fallback 仅覆盖 `tailwind`/`css`/`dtcg`；`style-dictionary` 可将同一份令牌编译到 **iOS / Android / SCSS** 等更多平台。集成方式：作为可选增强，包装为 `style-dictionary` 的 `build` 调用，补充官方 CLI fallback 不支持的多端输出。
- **colour-science/colour**：本项目在三个脚本各手写 `oklch`/`oklab`/`hwb` 与 WCAG 计算。`colour` 提供经验证的色彩空间转换与色差公式，可消除重复并提升边界正确性（如色域映射）。**权衡**：`colour` 体积大（README 73KB 量级），会显著加重 Python 依赖；若采用，建议仅引入所需子模块或自维护轻量封装。
- **Evercoder/culori**：JS 侧等价能力，主要价值在于为 `extraction.js` / `analyze_url.py` 未来可能的 Node 化提供参考实现；当前 Python 栈不必引入。
- **jasonhnd/design-md-generator**：直接竞品但 **2 Stars、近三个月无提交**，成熟度低，不足以作为复用来源；其"URL 反向提取"方向已被本项目 `--analyze-url` 覆盖。
- **VoltAgent/awesome-design-md**：96K Stars 为生态聚合列表（非单一工具），适合作为本项目上线后提交示例、获取曝光的渠道，与既有小红书推广互补。

### 2.2 调研结论

复用策略正确：**核心校验 / 导出已绑定官方 CLI**。下一步建议把**颜色数学**与**多端导出**两个自建环节分别向 `colour` 与 `style-dictionary` 靠拢，并借 `awesome-design-md` 做生态曝光。

---

## 三、架构与设计审查（扩展）

### 3.1 安全性（已确认达标）

路径遍历拒绝、YAML 注入中和、颜色输入校验与回退、子进程列表参数（无 `shell=True`）、URL 仅 `http/https`、原子写入——均由 1.6 节安全压测与初版审查确认达标。

### 3.2 性能（已确认达标）

见 1.4 节：亚毫秒级生成、0.088MB 峰值内存、截图 KMeans 有频率兜底。**无性能阻塞点**。

### 3.3 可扩展性

- **模板 / 组件硬编码**：12 模板存 `TEMPLATES` 字典，25+ 组件以三引号字符串内嵌；新增需改代码（P1）。
- **颜色 / 对比度数学三处重复**：三脚本各实现一份，维护一致性风险（P1）。
- **无插件 / 配置驱动机制**：对 Skill 场景可接受，但数据驱动可降扩展门槛（P1）。

### 3.4 代码规范与可维护性

- **仓库缺自动化测试（已落实）**：本版将 36 项断言沉淀为 `tests/` 冒烟套件并提交。
- **少量不可达代码**：`--tone` 的 CLI 层回退因 `argparse` `choices` 已拦截，仅 `--modify --set tone=...` 路径可达（功能正确，属冗余）。
- **上传包曾滞后（已修复）**：`new/` 与根目录现已字节一致，建议将"一致性检查"纳入提交前钩子。

### 3.5 数据库设计

**结论（已知事实）**：本项目为 **CLI / Skill**，生成静态 `DESIGN.md` 文件，**无数据库、无持久化状态、无 schema**。等价关注点是"输出原子性与幂等性"——已由 `tempfile` + `os.replace` 满足（见 1.5 节）。若未来引入模板 / 组件插件仓库，才需考虑轻量索引；当前不需要。

### 3.6 API 设计规范

**结论（已知事实 + 分析）**：项目无 HTTP API，对外接口即 `argparse` CLI。当前 CLI 设计一致（统一 `--name/--output/--template` 等、枚举 `choices`、清晰子命令），符合良好 CLI 规范。改进方向：
- 暴露**稳定程序化 API**（如 `generate(tokens) -> str`），便于被其他工具嵌入（P2）。
- 将 `print` 统一为 `logging` 模块 + `--quiet`/`--verbose` 开关，便于集成方捕获而非解析 stdout（P2）。

### 3.7 优化建议与优先级（含工作量估算）

| 优先级 | 优化项 | 说明 | 工作量 |
|--------|--------|------|--------|
| **P0（已落实）** | 依赖锁定 `requirements.txt` | 固定 `webcolors/pillow/numpy/scikit-learn` 版本，杜绝"在我机器上能跑" | 低（0.5 人天，已落实） |
| **P0（已落实）** | 冒烟测试进仓库 `tests/` | 防回归，CI 可跑 | 低（0.5 人天，已落实） |
| **P0** | 提交前校验 `root` 与 `new/` 字节一致 | 防止上传包再次滞后 | 低（0.5 人天，加 pre-commit / CI 步骤） |
| **P1** | 颜色 / 对比度数学集中化或采用 `colour` | 消除三处重复，提升 `oklch`/`oklab`/`hwb` 边界正确性 | 中（2~3 人天） |
| **P1** | 模板 / 组件数据驱动（外部 YAML） | 扩展无需改代码 | 中（2~3 人天） |
| **P1** | `analyze_url` 增加 mock / CI 集成测试 | 将覆盖率盲区从 9% 拉起 | 中（1~2 人天） |
| **P2** | 评估 `style-dictionary` 增强 `--export` | 补 iOS/Android/SCSS 多端 | 中（2 人天） |
| **P2** | 暴露稳定 Python API | 便于嵌入其他工具 | 低（1 人天） |
| **P2** | 统一 `logging` + `--quiet/--verbose` | 利于集成方捕获输出 | 低（1 人天） |
| **P2** | GitHub Actions CI | push 时跑冒烟测试 + `--check` | 低（0.5 人天） |

---

## 四、上线 Checklist

> 说明：本项目是 **Skill + CLI**，非 Web 服务，故"域名 / 证书 / 数据库"等项为 **N/A**，下表将其映射为等价检查项。

| 检查项 | 状态 | 说明 / 处置 |
|--------|------|--------------|
| **环境配置** | 已具备 | Python 3.8+（README 声明；实测 3.13.12 通过）；`node/npx` 供官方 CLI；`agent-browser` 供 `--analyze-url`（可选） |
| **依赖版本锁定** | **已落实** | 新增 `requirements.txt`，固定 `webcolors==25.10.0` / `pillow==12.3.0` / `numpy==2.5.1` / `scikit-learn==1.9.0` |
| **自动化测试** | **已落实** | `tests/` 冒烟套件已提交，36 项断言、零崩溃 |
| **上传包一致性（root ↔ new/）** | 已修复 | 字节一致；建议加 CI 步骤二次校验 |
| **日志 / 监控配置** | 待办（P2） | 当前为 `print`；建议改 `logging` + `--quiet/--verbose`；离线 CLI 无远程监控需求 |
| **回滚方案** | 建议 | Git 打 `vX.Y.Z` tag；RedSkill 可重新上传覆盖；保留上一版 tag 即可回滚 |
| **域名 / 证书检查** | N/A | 无对外服务；等价项：README 内链接（规范站、homepage）有效、RedSkill 元数据准确 |
| **安全复核** | 已通过 | 路径遍历 / YAML 注入 / 原子写 / 子进程安全均达标（见 1.6、3.1） |
| **发布阻塞项（历史）** | 已修复 | `new/` 同步 + `--modify` 原地覆盖 bug、`surfate` 拼写、`__pycache__` 清理 |

---

## 五、结论

**功能性**：36/36 断言通过，零崩溃；功能、边界、异常、并发、安全样本均稳健。

**性能**：单模板生成 0.53~0.85ms，内存峰值 0.088MB，无瓶颈。

**覆盖率**：核心引擎 69%、截图 81%；URL 反推 9% 为浏览器依赖的结构性盲区，已列为 P1 并给出测试方案。

**安全性**：路径遍历、YAML 注入、符号链接、超大 / NUL 输入均被安全处理。

**复用策略**：lint/diff/export 已绑定官方 CLI；下一步向 `colour`（颜色数学）与 `style-dictionary`（多端导出）靠拢。

**本次已落实的优化**：① 新增 `requirements.txt` 锁定依赖版本；② 提交 `tests/` 冒烟测试套件（36 项）。两项均为低风险、高价值的 P0 项，直接消除"依赖漂移"与"回归无 guardrail"两类上线风险。

**来源**：GitHub REST API（`api.github.com/repos/{owner}/{repo}` 及 `/issues`、`/readme`），检索于 2026-07-07；DESIGN.md 规范描述来自 `google-labs-code/design.md` 官方仓库。
