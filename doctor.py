#!/usr/bin/env python3
"""research-skills-pack 自检工具 (opencove 范式：一键体检入口)

课题组 git clone 后运行 `python3 doctor.py`，立刻知道：
- 7 个 skill 是否齐全
- 地基依赖（shared/research-base、tools/）是否就位
- 环境变量配了哪些、缺哪些（全部可选，缺了只降级不报错）
- supervisor-scout 的 Python 依赖是否安装

退出码：0 = 核心齐全可用，1 = 缺核心文件。
"""
import os
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent

G = "\033[32m"; R = "\033[31m"; Y = "\033[33m"; D = "\033[2m"; X = "\033[0m"


def ok(m): print(f"  {G}OK{X}   {m}")
def bad(m): print(f"  {R}MISS{X} {m}")
def opt(m): print(f"  {Y}--{X}   {m}")


# 按你的三层工作范式组织：调研 → 任务执行 → 输出
LAYERS = {
    "调研层": [
        "research", "academic-deep-research", "topic-framing", "method-design",
        "paper-discovery", "paper-screening", "paper-reading",
        "survey-writer", "paper-composer", "academic-plotting",
        "knowledge-compiler", "research-academic", "research-ideation",
        "rigor-reviewer", "supervisor-scout",
    ],
    "任务执行层": [
        "task-analyze", "task-decompose", "idea-to-research", "closeout",
    ],
    "输出层": [
        "output-layer", "output-polisher", "output-style-checker",
    ],
}
SKILLS = [s for layer in LAYERS.values() for s in layer]

# (skill, 工具文件) — 地基工具，跨 skill 复用
TOOLS = ["abstract_pipeline.py", "elsevier_fetch.py", "evidence_extractor.py"]

# 环境变量：全部可选，name -> (用途, 缺失时降级说明)
ENV_VARS = {
    "ELSEVIER_API_KEY": ("Elsevier 期刊 abstract 补全", "降级到 OpenAlex/SS/Crossref，覆盖率 ~50%"),
    "SEMANTIC_SCHOLAR_API_KEY": ("S2 abstract 补充源", "跳过 SS，用其他通路"),
    "STUDY_RESEARCH_ROOT": ("工具层根目录", "默认 ~/study-research"),
    "ANCHOR_POOL_DIR": ("closeout 锚点池", "跳过锚点扫描，只出 6 段总结"),
    "WORKSPACE_ROOT": ("idea-to-research 工作区根", "自动向上推断"),
    "HARVEST_TOOL_PATH": ("harvest-tool 位置", "仅 github-build 路线需要"),
}

# Python 依赖：import 名 -> (pip 名, 用途, 是否必需)
PY_DEPS = {
    "bs4": ("beautifulsoup4", "supervisor-scout 爬虫", True),
    "lxml": ("lxml", "supervisor-scout HTML 解析", True),
    "requests": ("requests", "supervisor-scout 网络请求", True),
    "pypinyin": ("pypinyin", "supervisor-scout 拼音生成", False),
}


def check_skills():
    print(f"\n{D}[1/4] Skills（{len(SKILLS)} 个，按三层分组）{X}")
    missing = 0
    for layer, names in LAYERS.items():
        print(f"  {D}· {layer}（{len(names)}）{X}")
        for s in names:
            skill_md = ROOT / "skills" / s / "SKILL.md"
            if skill_md.exists():
                ok(s)
            else:
                bad(f"{s}  — 缺 SKILL.md")
                missing += 1
    return missing


def check_foundation():
    print(f"\n{D}[2/4] 地基依赖{X}")
    missing = 0
    rb = ROOT / "shared" / "research-base" / "artifacts.md"
    if rb.exists():
        ok("shared/research-base（学术 skill 的底座 schema）")
    else:
        bad("shared/research-base — 缺 artifacts.md，paper-* / survey-writer 会失效")
        missing += 1
    for t in TOOLS:
        if (ROOT / "tools" / t).exists():
            ok(f"tools/{t}")
        else:
            bad(f"tools/{t} — paper-discovery/paper-reading 的 abstract 补全会降级")
            missing += 1
    return missing


def check_env():
    print(f"\n{D}[3/4] 环境变量（全部可选，缺了只降级不报错）{X}")
    for name, (use, fallback) in ENV_VARS.items():
        val = os.environ.get(name)
        if val:
            ok(f"{name}  — {use}")
        else:
            opt(f"{name}  未设 → {fallback}")


def check_py_deps():
    print(f"\n{D}[4/4] Python 依赖（supervisor-scout 爬虫用）{X}")
    missing_required = 0
    for mod, (pip_name, use, required) in PY_DEPS.items():
        found = importlib.util.find_spec(mod) is not None
        if found:
            ok(f"{pip_name}  — {use}")
        elif required:
            bad(f"{pip_name}  缺失 → pip3 install {pip_name}（{use}）")
            missing_required += 1
        else:
            opt(f"{pip_name}  未装（可选）→ {use}，缺了自动跳过")
    return missing_required


def main():
    print("=" * 56)
    print("  research-skills-pack 自检 (doctor)")
    print("=" * 56)

    core_missing = check_skills() + check_foundation()
    check_env()
    dep_missing = check_py_deps()

    print("\n" + "=" * 56)
    if core_missing == 0 and dep_missing == 0:
        print(f"  {G}全部就绪{X}：7 个 skill + 地基 + 必需依赖齐全，可直接用。")
        print(f"  {D}建议从 research skill 起步，或走 paper-discovery → paper-reading → survey-writer 链路。{X}")
        code = 0
    elif core_missing == 0:
        print(f"  {Y}核心就绪，缺必需 Python 依赖{X}：按上方 pip3 提示安装即可。")
        code = 0
    else:
        print(f"  {R}缺 {core_missing} 个核心文件{X}：克隆可能不完整，请重新 git pull 或联系维护者。")
        code = 1
    print("=" * 56)
    return code


if __name__ == "__main__":
    sys.exit(main())


