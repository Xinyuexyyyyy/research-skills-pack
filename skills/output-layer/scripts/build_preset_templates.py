#!/usr/bin/env python3
"""Build preset docx templates for output-layer.

Usage:
    python3 scripts/build_preset_templates.py

参考文档参数来源：
- formal-zh: /output/output-layer/20260520-192132-010051-openclaw-system-overview/output.docx
- memo-zh: /content work/output/output-layer/20260525-0020-hongguang-interview-docx/采访问题大纲_红光老师_临场增强版_排版优化.docx

Generates:
    templates/docx/formal-zh.docx        — 正式报告（openclaw 版面）
    templates/docx/formal-zh-no-number.docx — 轻量文档，标题不编号
    templates/docx/academic-zh.docx     — 学术论文，双倍行距+页码
    templates/docx/memo-zh.docx         — 内部备忘/采访，紧凑排版（hongguang 版面）
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_reference_doc.py"
OUTPUT_DIR = ROOT / "templates" / "docx"
BASE_REF = OUTPUT_DIR / "formal-zh-reference.docx"

# 参考 openclaw 输出 docx 实测参数：
# Normal line_spacing=28pt固定, space_before=10pt, space_after=14pt, first_indent=0.74cm
# Heading1=16pt bold, Heading2=14pt bold, Heading3=12pt bold
# Title=18pt(小二), Margins=2.54/3.17cm
PRESETS: dict[str, list[str]] = {
    "formal-zh": [
        "--body-font", "宋体", "--body-size", "小四",
        "--title-font", "黑体", "--title-size", "小二",
        "--heading-font", "黑体", "--heading1-size", "16",
        "--heading2-size", "14", "--heading3-size", "12",
        "--line-spacing", "28",
        "--first-line-indent", "2char",
        "--spacing-before", "10", "--spacing-after", "14",
        "--heading1-spacing-before", "10", "--heading1-spacing-after", "14",
        "--heading2-spacing-before", "10", "--heading2-spacing-after", "14",
        "--heading3-spacing-before", "8", "--heading3-spacing-after", "14",
        "--heading-align", "left",
        "--top-margin", "2.54", "--bottom-margin", "2.54",
        "--left-margin", "3.17", "--right-margin", "3.17",
    ],
    "formal-zh-no-number": [
        "--body-font", "宋体", "--body-size", "小四",
        "--title-font", "黑体", "--title-size", "小二",
        "--heading-font", "黑体", "--heading1-size", "16",
        "--heading2-size", "14", "--heading3-size", "12",
        "--line-spacing", "24",
        "--first-line-indent", "2char",
        "--spacing-before", "10", "--spacing-after", "14",
        "--heading1-spacing-before", "10", "--heading1-spacing-after", "14",
        "--heading2-spacing-before", "10", "--heading2-spacing-after", "14",
        "--heading3-spacing-before", "8", "--heading3-spacing-after", "14",
        "--heading-align", "left",
        "--top-margin", "2.54", "--bottom-margin", "2.54",
        "--left-margin", "3.17", "--right-margin", "3.17",
    ],
    "academic-zh": [
        "--body-font", "宋体", "--body-size", "小四",
        "--title-font", "黑体", "--title-size", "小二",
        "--heading-font", "黑体", "--heading1-size", "16",
        "--heading2-size", "14", "--heading3-size", "12",
        "--line-spacing", "28",
        "--first-line-indent", "2char",
        "--spacing-before", "10", "--spacing-after", "14",
        "--heading1-spacing-before", "10", "--heading1-spacing-after", "14",
        "--heading2-spacing-before", "10", "--heading2-spacing-after", "14",
        "--heading3-spacing-before", "8", "--heading3-spacing-after", "14",
        "--heading-align", "left",
        "--top-margin", "2.54", "--bottom-margin", "2.54",
        "--left-margin", "3.17", "--right-margin", "3.17",
        "--page-number", "on", "--page-number-align", "center",
    ],
    # 参考 hongguang 采访问题大纲排版优化版：
    # Normal line_spacing=1.15倍, space_before=10pt, space_after=14pt
    # Margins=1.76/1.65/2.01cm（窄边距，适合阅读/打印）
    "memo-zh": [
        "--body-font", "宋体", "--body-size", "小四",
        "--title-font", "黑体", "--title-size", "小二",
        "--heading-font", "黑体", "--heading1-size", "16",
        "--heading2-size", "14", "--heading3-size", "12",
        "--line-spacing", "1.15",
        "--first-line-indent", "2char",
        "--spacing-before", "10", "--spacing-after", "14",
        "--heading1-spacing-before", "10", "--heading1-spacing-after", "14",
        "--heading2-spacing-before", "10", "--heading2-spacing-after", "14",
        "--heading3-spacing-before", "8", "--heading3-spacing-after", "14",
        "--heading-align", "left",
        "--top-margin", "1.76", "--bottom-margin", "1.65",
        "--left-margin", "2.01", "--right-margin", "2.01",
    ],
}


def build_preset(name: str, args: list[str]) -> bool:
    output = OUTPUT_DIR / f"{name}.docx"
    cmd = [
        sys.executable, str(BUILDER),
        "--base-reference", str(BASE_REF),
        "--output", str(output),
        *args,
    ]
    print(f"Building {name} -> {output.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()}")
        return False
    size = output.stat().st_size
    print(f"  OK ({size:,} bytes)")
    return True


def main() -> int:
    if not BUILDER.exists():
        print(f"Builder not found: {BUILDER}")
        return 1
    if not BASE_REF.exists():
        print(f"Base reference not found: {BASE_REF}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name, args in PRESETS.items():
        if build_preset(name, args):
            ok += 1

    print(f"\nDone: {ok}/{len(PRESETS)} presets built.")
    return 0 if ok == len(PRESETS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
