#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_markdown_output.py"
DEFAULT_INPUT = ROOT / "samples" / "formal-report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quick entry for output-layer rendering.")
    parser.add_argument("input", nargs="?", default=str(DEFAULT_INPUT), help="Markdown source path")
    parser.add_argument("--profile", default="formal-zh", help="Profile name")
    parser.add_argument("--to", default="markdown,obsidian,docx,pdf", help="Comma-separated outputs")
    parser.add_argument("--rules", default="总标题黑体小二，正文仿宋GB2312小四，一级标题依赖正文，字体加粗，一级标题字号三号，段落规则固定28磅，非标题正文首行缩进2字符，标题段前空10磅段后空14磅，一级标题用一、二、三、，二级标题用1. 2. 3.，页码启用", help="Natural-language rule overrides")
    parser.add_argument("--outdir", default=str(ROOT / "output" / "output-layer"), help="Output base directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = [
        sys.executable,
        str(SCRIPT),
        str(Path(args.input).expanduser()),
        "--profile",
        args.profile,
        "--to",
        args.to,
        "--rules",
        args.rules,
        "--outdir",
        args.outdir,
    ]
    result = subprocess.run(command, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
