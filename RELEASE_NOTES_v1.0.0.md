# v1.0.0 — Design Spec Generator 首发版

> 离线、隐私友好的「文本 → DESIGN.md 设计规范生成引擎」  
> GitHub: https://github.com/LuckTerence/design-spec  
> 许可证: Apache 2.0

---

## 核心能力

- **文本 → DESIGN.md**：给品牌名 + 主色 + 模板风格，秒级生成完整设计规范（20+ 颜色令牌 / 12 级字阶 / 25+ 组件定义）
- **12 行业模板**：enterprise / ecommerce / finance / creative / healthcare / education / gaming / food-beverage / real-estate / travel / social-media / developer-tools
- **截图取色**：`--analyze` 截图 → MMCQ 提取主色 + 次要色 + 背景色 → 生成规范
- **外部导入对齐**：`--import` 可接收 designlang 等工具输出的 DESIGN.md，颜色归一入规范，正文无损
- **修改主色 / 导出 / 校验 / 差异对比**：`--modify` / `--export` / `--lint` / `--diff`

## 技术重构亮点

- 移除自研颜色数学（webcolors / numpy / scikit-learn），全部替换为 **coloraide + colorthief + Pillow**，依赖从 4 包降到 3 包
- 不再自研 URL 抽取，URL 场景委托 **designlang**（Manavarya09/design-extract, 2.5K★）— 聚焦护城河
- 新增 **pytest 测试套件**（29 项，核心引擎覆盖率 69%，截图 81%）
- 与 Google `@google/design.md` 生态对齐（lint / diff / export 优先调用官方 CLI）

## 架构策略

```
┌──────────────────────────────────────────────────┐
│               设计系统入口                         │
│  ┌──────────┐  ┌───────────┐  ┌────────────────┐  │
│  │文本生成   │  │截图分析    │  │--import 外部对齐│  │
│  └────┬─────┘  └─────┬─────┘  └───────┬────────┘  │
│       └───────┬──────┘                │           │
│               ▼                       │           │
│   ┌─────────────────────┐             │           │
│   │  coloraide (颜色)    │◄────────────┘           │
│   │  colorthief (取色)   │                        │
│   │  Pillow (图像)       │                        │
│   └─────────────────────┘                        │
│  ┌────────────────────────────────────────────────┐
│  │ 护城河：离线文本→DESIGN.md 生成引擎              │
│  └────────────────────────────────────────────────┘
│  ┌────────────────────────────────────────────────┐
│  │ 委托上游：designlang (URL抽取) / @google/design.md │
│  └────────────────────────────────────────────────┘
└──────────────────────────────────────────────────┘
```

## 文件结构

```
design-spec/
├── SKILL.md                         # WorkBuddy Skill 元数据
├── skill.json                       # RedSkill 上架清单
├── requirements.txt                 # coloraide/pillow/colorthief
├── scripts/
│   ├── generate_design_spec.py      # 主引擎 (~1980行)
│   └── analyze_screenshot.py        # 截图取色分析
├── references/
│   └── DESIGN.md                    # 完整字段示例
├── assets/
│   └── icon.svg                     # RedSkill 图标
├── tests/
│   └── test_design_spec.py          # 29 项 pytest
├── new/                             # RedSkill 发布包（与 root 字节一致）
└── dist/
    └── new.zip                      # 官方打包产物
```

## RedSkill 发布包

`dist/new.zip` 已通过 `package_skill.py` 校验（✅ Valid），可直接上传 RedSkill 市场。

## 安装与使用

```bash
pip install -r requirements.txt

# 一键生成 SaaS 后台规范
python scripts/generate_design_spec.py \
  --name "SaaS 后台" \
  --primary "#4F46E5" \
  --template enterprise

# 截图分析
python scripts/generate_design_spec.py \
  --analyze screenshot.png \
  --name "参考品牌"

# 导入外部 DESIGN.md
python scripts/generate_design_spec.py \
  --import designlang_output.md
```

---

**完整提交历史**：https://github.com/LuckTerence/design-spec/commits/main/
