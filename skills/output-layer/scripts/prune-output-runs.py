#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output" / "output-layer"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview output-layer run pruning.")
    parser.add_argument("command", nargs="?", default="plan")
    parser.add_argument("--topic-contains", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = ROOT / "output" / "output-prune-plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Output Prune Plan", ""]
    if OUTPUT_ROOT.exists():
        runs = sorted([p for p in OUTPUT_ROOT.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
        for run in runs:
            if args.topic_contains and args.topic_contains not in run.name:
                continue
            lines.append(f"- {run.name}")
    else:
        lines.append("- no runs found")
    plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"plan={plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
