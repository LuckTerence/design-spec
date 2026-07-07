#!/usr/bin/env python3
"""design-spec 冒烟测试套件（pytest）。

运行：
    pip install -r requirements.txt
    pytest tests/test_design_spec.py -q

覆盖率（可选）：
    pip install coverage pytest-cov
    coverage run -m pytest tests/ && coverage report
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
GEN = str(SCRIPTS / "generate_design_spec.py")
SHOT = str(SCRIPTS / "analyze_screenshot.py")
PY = sys.executable

# 前置依赖检查：核心生成依赖 coloraide，缺失则整体跳过
try:
    import coloraide  # noqa: F401
except ImportError:
    pytest.skip("coloraide 未安装，请先 pip install -r requirements.txt", allow_module_level=True)

WORK = tempfile.mkdtemp(prefix="ds_tests_")


def run(args, timeout=120):
    return subprocess.run([PY] + args, capture_output=True, text=True, timeout=timeout)


def gen(out, **kw):
    cmd = [GEN, "--name", kw.get("name", "Brand"), "--output", out]
    for k, v in kw.items():
        if k == "name":
            continue
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                cmd.append(flag)
            continue
        cmd += [flag, str(v)]
    return run(cmd)


TEMPLATES = ["enterprise", "ecommerce", "finance", "creative", "healthcare", "education",
             "gaming", "food-beverage", "real-estate", "travel", "social-media", "developer-tools"]


@pytest.mark.parametrize("tpl", TEMPLATES)
def test_all_templates(tpl):
    out = os.path.join(WORK, f"t_{tpl}.md")
    rc = gen(out, template=tpl, name=f"Brand{tpl}").returncode
    assert rc == 0 and os.path.exists(out)


def test_modify_derived_color_sync():
    base = os.path.join(WORK, "m.md")
    gen(base, name="M", primary="#1A73E8")
    rc = run([GEN, "--modify", base, "--set", "primary=#FF6600"]).returncode
    after = open(base).read()
    assert rc == 0 and 'primary: "#ff6600"' in after and "primary-hover" in after


def test_visualize_svg():
    vmd = os.path.join(WORK, "v.md")
    rc = gen(vmd, name="V", primary="#4F46E5", visualize=True).returncode
    vsvg = vmd.replace(".md", "_palette.svg")
    assert rc == 0 and os.path.exists(vsvg) and "<svg" in open(vsvg).read()


@pytest.mark.parametrize("fmt", ["tailwind", "css", "dtcg"])
def test_export_formats(fmt):
    emd = os.path.join(WORK, f"e_{fmt}.md")
    rc = gen(emd, name="E", primary="#10B981", export=fmt).returncode
    base = os.path.splitext(emd)[0]
    exp_map = {"tailwind": "_tailwind.theme.json", "css": "_tokens.css", "dtcg": "_tokens.json"}
    assert rc == 0 and os.path.exists(base + exp_map[fmt])


def test_check_self_check():
    assert run([GEN, "--check"]).returncode == 0


def test_lint_and_diff_wrappers():
    cmd = os.path.join(WORK, "chk.md")
    gen(cmd, name="C", primary="#6366F1")
    assert run([GEN, "--lint", cmd]).returncode in (0, 1)
    assert run([GEN, "--diff", cmd, cmd]).returncode in (0, 1)


def test_boundary_path_traversal():
    rc = gen(os.path.join(WORK, "../escape.md"), name="B").returncode
    assert rc != 0


def test_boundary_missing_name():
    rc = run([GEN, "--output", os.path.join(WORK, "b2.md")]).returncode
    assert rc != 0


def test_boundary_invalid_color_fallback():
    out = os.path.join(WORK, "b3.md")
    rc = gen(out, name="C", primary="不是颜色").returncode
    assert rc == 0 and os.path.exists(out)


def test_boundary_spacing_base_clamp():
    out = os.path.join(WORK, "b4.md")
    gen(out, name="S", spacing_base="100")
    assert "xs: 16px" in open(out).read()


def test_screenshot_analyze():
    try:
        from PIL import Image
        import colorthief  # noqa: F401
    except ImportError:
        pytest.skip("PIL 或 colorthief 未安装")
    png = os.path.join(WORK, "shot.png")
    Image.new("RGB", (400, 300), (30, 120, 200)).save(png)
    sout = os.path.join(WORK, "shot_out.md")
    rc = run([SHOT, png, "--colors", "5", "--output", sout]).returncode
    assert rc == 0 and os.path.exists(sout)


def test_import_mode():
    # 构造一个含非常规颜色格式的 DESIGN.md（designlang 类上游产物）
    src = os.path.join(WORK, "import_src.md")
    src_content = (
        "---\n"
        "version: \"alpha\"\n"
        "name: \"Imported\"\n"
        "colors:\n"
        "  background: \"#FFF\"\n"            # 3 位 hex
        "  primary: \"rgb(26, 115, 232)\"\n"  # rgb()
        "  text: \"oklch(80% 0 0)\"\n"        # oklch
        "  accent: \"not-a-color\"\n"          # 非法，应保留
        "---\n\n## Overview\n\nOriginal body kept.\n"
    )
    open(src, "w").write(src_content)
    out = os.path.join(WORK, "import_out.md")
    rc = run([GEN, "--import", src, "--output", out]).returncode
    assert rc == 0 and os.path.exists(out)
    txt = open(out).read()
    # 归一化结果：3 位→6 位、rgb()→hex、oklch→hex
    assert 'background: "#ffffff"' in txt
    assert 'primary: "#1a73e8"' in txt
    # 非法色保留原值且给出告警
    assert 'accent: "not-a-color"' in txt
    # 正文无损保留
    assert "Original body kept." in txt


def test_security_oversized_name():
    out = os.path.join(WORK, "big.md")
    rc = gen(out, name="A" * 10000).returncode
    assert rc == 0 and os.path.exists(out)


def test_security_yaml_injection():
    out = os.path.join(WORK, "inj.md")
    rc = gen(out, name="evil\nhacked: true").returncode
    content = open(out).read()
    fm = content.split("---")[1] if content.count("---") >= 2 else ""
    # 注入未成为独立 frontmatter 键
    assert rc == 0 and not any(l.strip().startswith("hacked:") for l in fm.splitlines())


def test_concurrency_distinct_processes():
    targets = [os.path.join(WORK, f"conc_{i}.md") for i in range(8)]
    procs = [subprocess.Popen([PY, GEN, "--name", f"C{i}", "--primary", "#0EA5E9", "--output", t])
             for i, t in enumerate(targets)]
    rcs = [p.wait() for p in procs]
    assert all(r == 0 and os.path.exists(t) for r, t in zip(rcs, targets))


def test_concurrency_race_no_corruption():
    race = os.path.join(WORK, "race.md")
    procs = [subprocess.Popen([PY, GEN, "--name", f"R{i}", "--primary", "#22C55E", "--output", race])
             for i in range(6)]
    [p.wait() for p in procs]
    valid = os.path.exists(race) and open(race).read().count("---") >= 2
    assert valid
