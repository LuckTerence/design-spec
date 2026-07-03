# design-spec Skill 安全审查与优化报告

**审查日期**：2026-07-04
**审查对象**：`scripts/generate_design_spec.py`、`scripts/analyze_screenshot.py`、`scripts/analyze_url.py`、`scripts/extraction.js`、`SKILL.md`
**审查维度**：安全漏洞、逻辑缺陷、性能瓶颈、Spec 合规性

---

## 一、问题清单与严重程度

### P0（高危）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **非法颜色回退值固定为 #1A73E8** | `generate_design_spec.py:validate_color` | background/text/secondary 等字段非法时也被回退到主色默认值，导致输出色板语义错乱 |
| 2 | **CSS 颜色格式支持名不副实** | `generate_design_spec.py:normalize_to_hex` | oklch/oklab/hwb/color-mix 通过正则校验却被静默转为 #808080；HSL 被错误转为灰阶；RGB 越界产生非法 hex |
| 3 | **路径遍历漏洞** | `generate_design_spec.py:main` | `--output` 可写入 `../etc/passwd` 等任意可写路径 |
| 4 | **浅色主题 `text-disabled` 比 `text-secondary` 更深** | `generate_design_spec.py:build_color_theme` | 语义错误：禁用文字应比次要文字更淡/更 muted |
| 5 | **迭代修改不更新派生色** | `generate_design_spec.py:modify_design_md` | 修改 primary 后 primary-hover/active/light 仍为旧值；修改 tone 后 error/success/warning/info 仍为旧值 |
| 6 | **截图分析 KMeans 失败路径崩溃** | `analyze_screenshot.py:extract_palette` | 异常分支后仍访问 `kmeans.labels_`，触发 AttributeError |
| 7 | **浏览器采样关键步骤失败后仍继续执行** | `analyze_url.py:run_agent_browser` | `open` 超时或失败后继续 `scroll`/`eval`，最终输出不可用的空结果 |

### P1（中危）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 8 | **YAML 注入防护不完整** | `generate_design_spec.py:escape_yaml` | 换行符、回车、Unicode 方向控制符、行首特殊字符可进入 YAML 标量 |
| 9 | **SVG 可视化硬编码深色背景** | `generate_design_spec.py:generate_palette_svg` | 浅色主题设计的 SVG 仍使用 #1e1e1e 背景，视觉不一致 |
| 10 | **SVG 不展示 accent-colors** | `generate_design_spec.py:generate_palette_svg` | 用户传入的强调色未在色板预览中体现 |
| 11 | **警告可能重复** | `generate_design_spec.py:main` | `--visualize` 会二次调用 `generate_yaml_frontmatter`，相同警告重复出现 |
| 12 | **导出 fallback 格式过时/不准确** | `generate_design_spec.py:_fallback_export` | Tailwind key 去掉所有 `-` 导致 `primary-hover` 变 `primaryhover`；CSS fallback 使用 `:root` 而非 Tailwind v4 的 `@theme`；DTCG 剥离单位 |
| 13 | **浏览器采样代码存在死代码与重复赋值** | `analyze_url.py:analyze_extracted` | `card_bg` 未使用、primary 赋值重复两行、`sampleElementRole` 从未调用 |
| 14 | **浏览器采样未校验 URL 协议** | `analyze_url.py:main` | 可传入 `file://`、`javascript:` 等危险协议 |
| 15 | **硬编码用户主目录路径** | `generate_design_spec.py:_find_npx` | `/Users/terencesai/...` 形式的绝对路径，Skill 分享给其他用户时回退失效 |
| 16 | **脚本输出包含 emoji** | `generate_design_spec.py:main` | 与用户"禁用 emoji"的偏好冲突 |
| 17 | **截图分析颜色语义推断差** | `analyze_screenshot.py:infer_semantic_colors` | 合成测试图中 primary 选择错误、surface/text 语义混乱 |
| 18 | **extraction.js 变量名冲突** | `scripts/extraction.js` | 顶层 `rs`（Set）与 try 块内 `const rs`（computedStyle）同名，易造成维护混淆 |

### P2（低危/建议）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 19 | **等宽字体族推导生成不存在的 `Inter-Mono`** | `generate_design_spec.py:generate_yaml_frontmatter` | 代码字体可能无法命中系统字体 |
| 20 | **主题判断使用平均 RGB 而非相对亮度** | `generate_design_spec.py:is_dark_bg` | 高饱和颜色可能被误判为背景深浅 |
| 21 | `--analyze`/`--analyze-url` 与其他参数互斥 | `generate_design_spec.py:main` | 无法同时 `--analyze screenshot.png --export css` |
| 22 | **模板电商/金融主色对比度不足** | `generate_design_spec.py:TEMPLATES` | 默认生成即触发 WCAG AA 警告 |
| 23 | **自检 `npx @google/design.md --version` 可能因网络阻塞** | `generate_design_spec.py:run_self_check` | 首次自检耗时不可控 |

---

## 二、优化方案与实现

### P0

| # | 优化方案 | 实现位置 |
|---|----------|----------|
| 1 | 引入字段级默认回退表 `FIELD_DEFAULTS`，按字段返回对应默认值 | `FIELD_DEFAULTS` + `validate_color` |
| 2 | 重写 `normalize_to_hex`：支持 hex/rgb/hsl/oklch/oklab/hwb/transparent/命名颜色；RGB 分量 clamp 到 0-255；HSL 真实转 RGB；Oklab/Oklch 通过 XYZ(D65) 转 sRGB；HWB 按 CSS Color 4 算法转换；越界或不可解析时抛出 `ValueError` | `normalize_to_hex` |
| 3 | 输出路径经过 `resolve_output_path` 校验：拒绝包含 `..` 的段；原子写入仅在解析后的目录内进行 | `resolve_output_path` + `safe_write` |
| 4 | 浅色主题 `text-disabled` 改为 `darken_color(background, 0.30)`，确保比 `text-secondary` 更浅 | `build_color_theme` |
| 5 | 将 `modify_design_md` 由正则替换改为"解析原参数 → 应用覆盖 → 重新生成"，派生色随基础色同步更新 | `modify_design_md` + `parse_yaml_frontmatter` |
| 6 | KMeans 异常分支改用 frequency-based fallback，重新构造 `cluster_colors` 与 `labels`，避免访问未初始化的 KMeans 属性 | `extract_palette` |
| 7 | 浏览器采样改为显式步骤检查：open 失败立即关闭浏览器并退出；scroll/wait/eval 分别处理超时；最后统一 close | `run_agent_browser` |

### P1

| # | 优化方案 | 实现位置 |
|---|----------|----------|
| 8 | `escape_yaml` 在转义前先替换真实换行/回车/制表符为空格，并替换字面 `\n`/`\r`；移除 Unicode 方向控制符与空字符 | `escape_yaml` |
| 9 | SVG 背景与文字色根据 `theme.is_dark` 动态选择（深色主题 #1e1e1e，浅色主题 #f8f9fa） | `generate_palette_svg` |
| 10 | SVG 增加 "强调色" 分组，渲染 `args.accent_colors` | `generate_palette_svg` |
| 11 | 引入 `WarningCollector` 去重集合；`WARNINGS` 每次 `main()` 重新实例化 | `WarningCollector` |
| 12 | Tailwind fallback 保留 `-` 为 key；CSS fallback 输出 Tailwind v4 `@theme` 语法；DTCG spacing 保留带单位字符串 | `_fallback_export` |
| 13 | 删除 `sampleElementRole`、去重 `result["colors"]["primary"]`、移除未使用的 `card_bg` 逻辑 | `analyze_url.py` |
| 14 | 新增 `validate_url`，仅允许 `http`/`https` 协议，拒绝空 host | `validate_url` |
| 15 | `_find_npx` 通过 `os.path.expanduser("~")` 动态构造 WorkBuddy 路径，支持多用户 | `_find_npx` |
| 16 | 移除所有 emoji，改用纯文本标识 | 全脚本 |
| 17 | 重写 `infer_semantic_colors`：background 优先选中性最大占比；text 选与背景对比最高且排除背景本身；primary 选非中性高饱和且非文字色；surface 选第二中性色；secondary 选与已用色差异明显的颜色 | `infer_semantic_colors` |
| 18 | JS 中顶层 Set 改名为 `colorSet`/`fontSet`/`roundedSet`/`elementSigSet`，与 `rootStyle` 区分 | `extraction.js` |

### P2

| # | 优化方案 | 实现位置 |
|---|----------|----------|
| 19 | 等宽字体默认使用 `DEFAULT_MONO_FONT`（JetBrains Mono / SF Mono / Fira Code），仅在用户指定字体时才尝试派生 `*-Mono` | `generate_yaml_frontmatter` |
| 20 | `is_dark_bg` 改为基于 WCAG 相对亮度，阈值 0.179 | `is_dark_bg` |
| 21 | 当前保持反向工程模式独立退出；文档中说明 `--analyze`/`--analyze-url` 与 `--export`/`--visualize` 不组合使用 | `SKILL.md` |
| 22 | 调整 ecommerce primary 为 #C2185B，finance primary 为 #0A753D，均满足 WCAG AA 与白色对比 | `TEMPLATES` |
| 23 | 自检提示改为 `npx agent-browser` / `npx @google/design.md`，不强制安装全局包 | `run_self_check` |

---

## 三、验证结果

| 场景 | 结果 |
|------|------|
| 正向生成 | 通过，text-disabled 语义正确 |
| 非法颜色回退 | 通过，background 回退 #FFFFFF，primary 回退 #1A73E8 |
| CSS 颜色格式（rgb/hsl/oklch） | 通过，均正确归一化为 sRGB hex |
| 路径遍历 | 通过，含 `..` 路径被拒绝并返回非零退出码 |
| YAML 注入 | 通过，换行与引号被转义或替换为空格 |
| 深色主题 + SVG | 通过，SVG 背景随主题切换 |
| 迭代修改 | 通过，primary-hover/active/light 与 tone 语义色同步更新 |
| 导出 | 通过，优先官方 CLI，fallback 输出 `@theme` 语法 |
| 截图分析 | 通过，KMeans fallback 安全，颜色含置信度与质量备注 |
| 模板 | 通过，电商/金融模板不再触发对比度警告 |
| 中文字体 | 通过，中文品牌名自动切换 PingFang SC 字体族 |
| 自检 | 通过，核心依赖与可选工具均识别正常 |

---

## 四、仍存在的已知限制

1. **截图分析本质是启发式像素推断**：无法区分按钮与背景的真实语义角色，复杂页面需要人工校验。
2. **浏览器采样依赖 `agent-browser` 外部 CLI**：未安装时该功能不可用。
3. **颜色空间转换精度**：Oklab/Oklch 到 sRGB 使用 D65 白点近似，极端色域值可能略有偏差。
4. **路径安全策略**：仅阻止 `..` 段；若用户传入指向系统目录的绝对路径，仍会按文件系统权限处理。

---

## 五、优化后的关键文件

- `scripts/generate_design_spec.py`（主脚本，完整重写）
- `scripts/analyze_screenshot.py`（截图分析引擎，修复崩溃并改进推断）
- `scripts/analyze_url.py`（浏览器采样引擎，清理死代码并增强健壮性）
- `scripts/extraction.js`（页面样式提取脚本，变量名规范与采样增强）
- `SKILL.md`（文档同步更新）
