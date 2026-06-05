#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output" / "output-layer"


def main() -> int:
    if not OUTPUT_ROOT.exists():
        print("output-layer output 目录不存在")
        return 0
    runs = sorted([p for p in OUTPUT_ROOT.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    for run in runs[:20]:
        manifest = run / "manifest.json"
        print(f"{run.name} | manifest={'yes' if manifest.exists() else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
