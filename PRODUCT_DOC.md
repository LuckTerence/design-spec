# design-spec Skill 产品需求文档

## 产品定位

一个能完成"正向生成 + 反向工程 + 代码导出"全链路的设计规范生成工具，对齐 google-labs-code/design.md 规范。

**开源声明**：本 Skill 所有功能纯本地运行，无需任何 API 密钥。外部依赖均为开源库（webcolors / Pillow / scikit-learn / @google/design.md），许可证兼容开源。

## 用户场景

1. **从零开始**：产品经理/设计师描述品牌与设计方向 → 自动生成 DESIGN.md
2. **从现有产品反推**：给一个 URL 或截图 → 提取实际设计语言 → 生成 DESIGN.md
3. **落地到工程**：DESIGN.md → 输出 Tailwind / CSS / DTCG 等工程文件

## 已实现功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 正向生成 | 输入名称/调性/色板生成 DESIGN.md | 已完成 |
| 安全防护 | 颜色校验 / YAML 注入防护 / WCAG 对比度 / 原子写入 / 路径遍历防护 | 已完成 |
| 行业模板 | enterprise/ecommerce/finance/creative/healthcare/education/gaming/food-beverage/real-estate/travel/social-media/developer-tools 12 种 | 已完成 |
| 深色主题 | 自动识别深色背景，切换阴影/颜色推导 | 已完成 |
| 色板可视化 | --visualize 生成 SVG 色板预览 | 已完成 |
| 迭代修改 | --modify + --set 局部更新已有 DESIGN.md，派生色同步重算 | 已完成 |
| 多语言字体 | 中文名称自动匹配 PingFang SC | 已完成 |
| Spec 合规 | 组件属性对齐 google-labs-code/design.md alpha 规范 | 已完成 |
| 代码导出 | --export tailwind/css/dtcg，优先调用官方 CLI，失败时本地 fallback | 已完成 |
| 截图分析 | --analyze，从截图提取色板并推断语义角色 | 已完成 |
| 浏览器采样 | --analyze-url，基于 agent-browser 提取真实页面样式 | 已完成 |
| 校验与比对 | --lint / --diff，直接桥接官方 @google/design.md CLI，不重复实现规则 | 已完成 |

## 已知限制

正向生成、反向工程、代码导出、校验比对四条主链路均已完成，当前不再规划新的功能模块，剩下的是已知的能力边界：

1. **截图分析是启发式像素推断**：无法区分按钮与背景的真实语义角色，复杂页面建议人工复核。
2. **浏览器采样依赖外部 CLI**：`--analyze-url` 需要预装 `agent-browser`，未安装时该功能不可用。
3. **`--lint`/`--diff` 无本地兜底**：与 `--export` 不同，这两个命令完全依赖 `@google/design.md` 官方 CLI，未安装会直接报错。
4. **颜色空间转换存在精度误差**：Oklab/Oklch 到 sRGB 基于 D65 白点近似，极端色域值可能略有偏差。
5. **路径安全策略仅阻止 `..` 段**：若用户显式传入指向系统目录的绝对路径，仍按文件系统权限处理。

## CLI 命令索引（当前）

| 参数 | 说明 |
|------|------|
| `--name NAME` | 设计系统名称 |
| `--description TEXT` | 品牌或产品描述 |
| `--template {...}` | 12 种行业模板之一，详见 SKILL.md |
| `--theme {light,dark,auto}` | 主题模式，默认 auto（按背景亮度判断） |
| `--primary/--secondary/--background/--text` | 色板配置（CSS 颜色格式） |
| `--font` | 字体族 |
| `--tone` | 设计调性（专业/活泼/极简/科技/优雅） |
| `--accent-colors` | 额外强调色，可传多个 |
| `--spacing-base` | 间距网格基准像素，默认 4 |
| `--version` | DESIGN.md 规范版本，默认 alpha |
| `--output PATH` | 输出路径（拒绝 `..` 目录遍历） |
| `--timestamp` | 输出文件名追加日期后缀 |
| `--visualize` | 同时生成 SVG 色板预览 |
| `--modify FILE --set KEY=VALUE` | 对已有文件做局部修改，派生色自动重算 |
| `--export {tailwind,css,dtcg}` | 导出工程文件格式（可重复使用，优先走官方 CLI） |
| `--analyze PATH` | 分析截图并提取设计令牌 |
| `--analyze-url URL` | 分析网页并提取设计令牌（依赖 agent-browser） |
| `--lint FILE` | 调用官方 CLI 校验 DESIGN.md |
| `--diff FILE1 FILE2` | 调用官方 CLI 比较两个版本的差异 |
| `--check` | 检查环境依赖是否就绪 |

## 交付物

- DESIGN.md（设计规范文档，核心输出）
- \*\_palette.svg（可选色板预览）
- \*\_tailwind.theme.json（Tailwind v3 配置）
- \*\_tokens.css（CSS 自定义属性，Tailwind v4 `@theme` 语法）
- \*\_tokens.json（W3C DTCG 标准格式，可直接被 Style Dictionary 等工具消费）
- lint/diff 结果直接打印到终端，不产生独立文件
