#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = ROOT / "scripts" / "render_markdown_output.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified output-layer entry point.")
    parser.add_argument("input", help="Markdown source path")
    parser.add_argument("--scene", default="academic", choices=["academic", "report", "obsidian", "media"], help="Target scene")
    return parser.parse_args()


def _scene_to_profile(scene: str) -> tuple[str, str]:
    mapping = {
        "academic": ("formal-zh", "markdown,obsidian,docx"),
        "report": ("formal-zh", "markdown,obsidian,docx,pdf"),
        "obsidian": ("formal-zh", "markdown,obsidian"),
        "media": ("formal-zh", "markdown,obsidian,docx"),
    }
    return mapping[scene]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _human_reason(statuses: dict[str, dict[str, str]]) -> str:
    reasons = []
    for key in ["docx", "pdf", "obsidian", "markdown"]:
        info = statuses.get(key, {})
        if info.get("status") in {"failed", "blocked"} and info.get("reason"):
            reasons.append(f"{key}: {info['reason']}")
    return "; ".join(reasons)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    profile, outputs = _scene_to_profile(args.scene)

    command = [
        sys.executable,
        str(RENDER_SCRIPT),
        str(input_path),
        "--profile",
        profile,
        "--to",
        outputs,
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print("输出失败：核心渲染脚本执行失败。")
        if exc.stderr:
            print(exc.stderr.strip())
        return 1

    run_dir = None
    manifest_path = None
    for line in result.stdout.splitlines():
        if line.startswith("run_dir="):
            run_dir = Path(line.split("=", 1)[1].strip())
        if line.startswith("manifest="):
            manifest_path = Path(line.split("=", 1)[1].strip())

    if not manifest_path or not manifest_path.exists():
        print("输出失败：没有找到 manifest.json。")
        return 1

    manifest = _read_json(manifest_path)
    artifacts = manifest.get("artifacts", {})
    statuses = manifest.get("statuses", {})
    report = {
        "input": str(input_path),
        "scene": args.scene,
        "success": all(statuses.get(name, {}).get("status") in {"written", "skipped"} for name in ["markdown", "obsidian", "docx"]),
        "run_dir": str(run_dir) if run_dir else "",
        "manifest": str(manifest_path),
        "files": [],
        "sizes": {},
        "reason": _human_reason(statuses),
    }

    for name in ["markdown", "obsidian", "docx", "pdf", "style_correction_report", "style_correction_report_md", "manifest", "index"]:
        path_text = artifacts.get(name)
        if not path_text:
            continue
        path = Path(path_text)
        if path.exists():
            report["files"].append(str(path))
            report["sizes"][path.name] = path.stat().st_size

    report_path = (run_dir or manifest_path.parent) / "output_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    docx_path = artifacts.get("docx")
    docx_msg = Path(docx_path).name if docx_path else "无 docx"
    clean_path = artifacts.get("markdown")
    obsidian_path = artifacts.get("obsidian")
    clean_msg = Path(clean_path).name if clean_path else "无 clean.md"
    obsidian_msg = Path(obsidian_path).name if obsidian_path else "无 obsidian.md"

    print(f"已生成 3 个文件：{clean_msg}, {obsidian_msg}, {docx_msg}。")
    if report["reason"]:
        print(f"附注：{report['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
