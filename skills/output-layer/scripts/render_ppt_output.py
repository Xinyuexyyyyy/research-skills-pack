#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _detect_workspace_root() -> Path:
    candidates: list[Path] = []
    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])
    script_path = Path(__file__).resolve()
    candidates.extend([script_path.parent, *script_path.parents])

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "skills" / "ppt-master").exists() and (candidate / "skills" / "ppt-master-bridge").exists():
            return candidate
    raise FileNotFoundError("workspace root not found for output-layer ppt pipeline")


ROOT = _detect_workspace_root()
OUTPUT_LAYER_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = OUTPUT_LAYER_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from artifact_writer import create_run_dir, write_manifest

PPT_BRIDGE = ROOT / "skills" / "ppt-master-bridge" / "scripts" / "bridge.py"
PPT_MASTER_ROOT = ROOT / "skills" / "ppt-master"
PPT_MASTER_SKILL_ROOT = PPT_MASTER_ROOT / "skills" / "ppt-master"
PPT_PROJECTS_DIR = PPT_MASTER_ROOT / "projects"
PROJECT_MANAGER = PPT_MASTER_SKILL_ROOT / "scripts" / "project_manager.py"
PPT_MASTER_SCRIPTS_DIR = PPT_MASTER_SKILL_ROOT / "scripts"
TOTAL_MD_SPLIT = PPT_MASTER_SKILL_ROOT / "scripts" / "total_md_split.py"
FINALIZE_SVG = PPT_MASTER_SKILL_ROOT / "scripts" / "finalize_svg.py"
SVG_TO_PPTX = PPT_MASTER_SKILL_ROOT / "scripts" / "svg_to_pptx.py"

if str(PPT_MASTER_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PPT_MASTER_SCRIPTS_DIR))

from project_utils import CANVAS_FORMATS, get_project_info

PRESET_CONFIGS: dict[str, dict[str, Any]] = {
    "pitch": {
        "mode": "pitch-deck",
        "research_kind": "",
        "page_count": 10,
        "goal": "先生成对外说服型 PPT 上游交接包",
    },
    "research-academic": {
        "mode": "research-deck",
        "research_kind": "academic",
        "page_count": 8,
        "goal": "先生成学术汇报型 PPT 上游交接包",
    },
    "research-weekly": {
        "mode": "research-deck",
        "research_kind": "group-weekly",
        "page_count": 7,
        "goal": "先生成组会周报型 PPT 上游交接包",
    },
    "research-intro": {
        "mode": "research-deck",
        "research_kind": "intro-share",
        "page_count": 8,
        "goal": "先生成介绍类分享 PPT 上游交接包",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a PPT upstream package via output-layer by calling ppt-master-bridge."
    )
    parser.add_argument("--topic", required=True, help="PPT 主题")
    parser.add_argument("--audience", default="", help="听众 / 对象")
    parser.add_argument("--goal", default="", help="这份 PPT 想达成什么")
    parser.add_argument("--core-message", default="", help="一句话核心表达")
    parser.add_argument(
        "--preset",
        choices=sorted(PRESET_CONFIGS.keys()),
        default="",
        help="常用 PPT 预设：路演、学术汇报、组会周报、介绍类分享。",
    )
    parser.add_argument("--mode", choices=["general", "pitch-deck", "research-deck"], default="research-deck")
    parser.add_argument(
        "--research-kind",
        choices=["academic", "group-weekly", "intro-share"],
        default="intro-share",
        help="仅 research-deck 使用",
    )
    parser.add_argument("--scope", default="", help="范围边界")
    parser.add_argument("--language", default="zh-CN", help="语言")
    parser.add_argument("--page-count", type=int, default=8, help="目标页数")
    parser.add_argument(
        "--stage",
        choices=["upstream", "full"],
        default="upstream",
        help="upstream=只生成 bridge 上游包；full=在满足条件时继续尝试下游导出 pptx",
    )
    parser.add_argument(
        "--project-name",
        default="",
        help="可选：指定 bridge 项目名；不传则按 topic 自动生成",
    )
    parser.add_argument(
        "--project-path",
        default="",
        help="可选：直接复用已有 ppt-master 项目目录",
    )
    parser.add_argument(
        "--research-route",
        choices=["github-build", "product-research", "social-research"],
        default="",
        help="可选：强制指定 idea-to-research 路线",
    )
    parser.add_argument(
        "--build-downstream",
        action="store_true",
        help="可选：上游完成后，继续提示或接下游 ppt-master 流程（当前只输出 handoff，不自动全链导出）",
    )
    parser.add_argument(
        "--outdir",
        default=str(ROOT / "output" / "output-layer"),
        help="output-layer 运行目录根路径",
    )
    return parser.parse_args()


def _argv_has_flag(flag: str) -> bool:
    return any(item == flag or item.startswith(f"{flag}=") for item in sys.argv[1:])


def _apply_preset(args: argparse.Namespace) -> argparse.Namespace:
    preset_name = str(getattr(args, "preset", "")).strip()
    if not preset_name:
        return args
    preset = PRESET_CONFIGS[preset_name]
    if not _argv_has_flag("--mode"):
        args.mode = str(preset["mode"])
    if args.mode == "research-deck" and not _argv_has_flag("--research-kind") and preset.get("research_kind"):
        args.research_kind = str(preset["research_kind"])
    if not _argv_has_flag("--page-count"):
        args.page_count = int(preset["page_count"])
    if not _argv_has_flag("--goal") and preset.get("goal"):
        args.goal = str(preset["goal"])
    return args


def _slugify(text: str) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower()).strip("-")
    return base or "ppt-output"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def _ensure_bridge_exists() -> None:
    if not PPT_BRIDGE.exists():
        raise FileNotFoundError(f"ppt bridge not found: {PPT_BRIDGE}")


def _resolve_project_path(args: argparse.Namespace) -> Path:
    if args.project_path:
        return Path(args.project_path).expanduser().resolve()
    project_name = args.project_name.strip() or _slugify(args.topic)
    return PPT_PROJECTS_DIR / project_name


def _ensure_project(project_path: Path) -> tuple[Path, bool]:
    if project_path.exists():
        return project_path, False
    project_name = project_path.name
    init = _run(
        [sys.executable, str(PPT_BRIDGE), "init", project_name, "--format", "ppt169"],
        ROOT,
    )
    if init.returncode != 0:
        details = (init.stderr or init.stdout or "").strip()
        if "Project directory already exists" not in details:
            raise RuntimeError(details or "bridge init failed")
        candidates = sorted(PPT_PROJECTS_DIR.glob(f"{project_name}*"), key=lambda item: item.stat().st_mtime, reverse=True)
        if candidates:
            return candidates[0].resolve(), False
        raise RuntimeError(details or "bridge init failed")
    stdout = (init.stdout or "").strip()
    matches = re.findall(r"/Users/.+", stdout)
    if matches:
        created = Path(matches[-1].strip()).resolve()
        if created.exists():
            return created, True
    candidates = sorted(PPT_PROJECTS_DIR.glob(f"{project_name}*"), key=lambda item: item.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0].resolve(), True
    raise RuntimeError("bridge init succeeded but created project path could not be resolved")


def _run_upstream(project_path: Path, args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(PPT_BRIDGE),
        "upstream",
        str(project_path),
        "--mode",
        args.mode,
        "--topic",
        args.topic,
        "--audience",
        args.audience,
        "--goal",
        args.goal or "先生成可进入 ppt-master 的上游交接包",
        "--core-message",
        args.core_message or args.topic,
        "--scope",
        args.scope or "聚焦当前主题最小闭环",
        "--language",
        args.language,
        "--page-count",
        str(args.page_count),
    ]
    if args.mode == "research-deck":
        cmd.extend(["--research-kind", args.research_kind])
    if args.research_route:
        cmd.extend(["--research-route", args.research_route])
    result = _run(cmd, ROOT)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(details or "bridge upstream failed")


def _newest_pptx(project_path: Path) -> Path | None:
    exports_dir = project_path / "exports"
    if not exports_dir.exists():
        return None
    pptx_files = sorted(exports_dir.glob("*.pptx"), key=lambda item: item.stat().st_mtime, reverse=True)
    return pptx_files[0] if pptx_files else None


def _run_step(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def _status_entry(status: str, reason: str = "", code: str = "ok", details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "code": code,
        "reason": reason,
    }
    if details is not None:
        payload["details"] = details
    return payload


def _prepare_downstream_seed(project_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    statuses: dict[str, dict[str, Any]] = {}
    artifacts: dict[str, str] = {}
    steps = [
        (
            "ppt_bridge_brief",
            "bridge_briefing",
            [sys.executable, str(PROJECT_MANAGER), "bridge-brief", str(project_path)],
            project_path / "sources" / "bridge_briefing.md",
            "bridge_brief_failed",
        ),
        (
            "ppt_strategist_seed",
            "strategist_seed",
            [sys.executable, str(PROJECT_MANAGER), "strategist-seed", str(project_path)],
            project_path / "strategist_seed.md",
            "strategist_seed_failed",
        ),
    ]
    for status_key, artifact_key, command, expected_path, error_code in steps:
        result = _run_step(command, ROOT)
        if result.returncode != 0:
            reason = (result.stderr or result.stdout or "").strip() or f"{status_key} failed"
            statuses[status_key] = _status_entry("failed", reason=reason, code=error_code)
            continue
        statuses[status_key] = _status_entry("written")
        artifacts[artifact_key] = str(expected_path)
    return statuses, artifacts


def _load_bridge_manifest(project_path: Path) -> dict[str, Any]:
    path = project_path / "bridge_manifest.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_downstream_kickoff(project_path: Path) -> Path:
    manifest = _load_bridge_manifest(project_path)
    topic = str(manifest.get("topic", project_path.name)).strip() or project_path.name
    mode = str(manifest.get("mode", "general")).strip() or "general"
    research_kind = str(manifest.get("research_kind", "")).strip()
    audience = str(manifest.get("audience", "待补充")).strip() or "待补充"
    goal = str(manifest.get("goal", "待补充")).strip() or "待补充"
    core_message = str(manifest.get("core_message", "待补充")).strip() or "待补充"
    page_count = str(manifest.get("page_count", "待补充")).strip() or "待补充"
    kind_suffix = f" / {research_kind}" if research_kind else ""
    lines = [
        "# Downstream Kickoff",
        "",
        "> 这是给 `ppt-master` 下游 Strategist 的起步包，不是最终确认结果，也不是正式 `design_spec.md / spec_lock.md`。",
        "",
        "## 项目摘要",
        "",
        f"- Topic: {topic}",
        f"- Mode: {mode}{kind_suffix}",
        f"- Audience: {audience}",
        f"- Goal: {goal}",
        f"- Core message: {core_message}",
        f"- Page count: {page_count}",
        "",
        "## 先读这些文件",
        "",
        f"- `{project_path / 'consensus.md'}`",
        f"- `{project_path / 'research.md'}`",
        f"- `{project_path / 'storyboard.md'}`",
        f"- `{project_path / 'handoff.md'}`",
        f"- `{project_path / 'sources' / 'bridge_briefing.md'}`",
        f"- `{project_path / 'strategist_seed.md'}`",
        "",
        "## 当前还不能跳过的步骤",
        "",
        "- 必须先完成 `Eight Confirmations`，不能直接假装已经定稿。",
        "- `strategist_seed.md` 只是第一轮推荐稿，不替代用户确认。",
        "",
        "## Eight Confirmations 清单",
        "",
        "1. Canvas format",
        "2. Page count range",
        "3. Target audience",
        "4. Style objective",
        "5. Color scheme",
        "6. Icon usage approach",
        "7. Typography plan",
        "8. Image usage approach",
        "",
        "## 确认后该做什么",
        "",
        f"- 按模板起正式 `design_spec.md`：`{PPT_MASTER_SKILL_ROOT / 'templates' / 'design_spec_reference.md'}`",
        f"- 按模板起正式 `spec_lock.md`：`{PPT_MASTER_SKILL_ROOT / 'templates' / 'spec_lock_reference.md'}`",
        "- 确认 `svg_output/` 生成完成后，再回到 `output-layer` 跑 `--stage full`。",
        "",
        "## 回到 output-layer 的命令",
        "",
        "```bash",
        "python3 skills/output-layer/scripts/render_ppt_output.py \\",
        f"  --topic \"{topic}\" \\",
        "  --stage full \\",
        f"  --project-path \"{project_path}\"",
        "```",
        "",
    ]
    path = project_path / "downstream_kickoff.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _render_design_spec_starter(project_path: Path, manifest: dict[str, Any]) -> str:
    project_info = get_project_info(str(project_path))
    canvas_key = str(project_info.get("format", "ppt169"))
    canvas_info = CANVAS_FORMATS.get(canvas_key, CANVAS_FORMATS["ppt169"])
    project_name = project_info.get("name", project_path.name)
    topic = str(manifest.get("topic", project_name)).strip() or str(project_name)
    audience = str(manifest.get("audience", "待在八项确认中确认")).strip() or "待在八项确认中确认"
    goal = str(manifest.get("goal", "待在八项确认中确认")).strip() or "待在八项确认中确认"
    core_message = str(manifest.get("core_message", "待在八项确认中确认")).strip() or "待在八项确认中确认"
    page_count = str(manifest.get("page_count", "待确认")).strip() or "待确认"
    mode = str(manifest.get("mode", "general")).strip() or "general"
    research_kind = str(manifest.get("research_kind", "")).strip()
    storyboard_pages = manifest.get("storyboard_pages", [])
    storyboard_lines: list[str] = []
    if isinstance(storyboard_pages, list):
        for row in storyboard_pages:
            if not isinstance(row, dict):
                continue
            page = str(row.get("page", "")).strip() or "??"
            role = str(row.get("role", "")).strip() or "content"
            key_message = str(row.get("key_message", "")).strip() or "待补充"
            evidence = str(row.get("evidence", "")).strip() or "待补充"
            storyboard_lines.extend(
                [
                    f"#### Slide {page} - {role}",
                    "",
                    f"- **Title**: {key_message}",
                    f"- **Content**: {evidence}",
                    "",
                ]
            )
    kind_suffix = f" / {research_kind}" if research_kind else ""
    lines = [
        f"# {project_name} - Design Spec Starter",
        "",
        "> Starter only. 这是 `Eight Confirmations` 前的起稿版本，不是正式 `design_spec.md`，不能替代 Strategist 定稿。",
        "",
        "## I. Project Information",
        "",
        "| Item | Value |",
        "| ---- | ----- |",
        f"| **Project Name** | {project_name} |",
        f"| **Canvas Format** | {canvas_info['name']} ({canvas_info['dimensions']}) |",
        f"| **Page Count** | {page_count} |",
        f"| **Design Style** | 待在 Eight Confirmations 中确认 |",
        f"| **Target Audience** | {audience} |",
        f"| **Use Case** | {goal} |",
        "",
        "## II. Canvas Specification",
        "",
        "| Property | Value |",
        "| -------- | ----- |",
        f"| **Format** | {canvas_info['name']} |",
        f"| **Dimensions** | {canvas_info['dimensions']} |",
        f"| **viewBox** | `{canvas_info['viewbox']}` |",
        "",
        "## III. Upstream Intake",
        "",
        f"- Topic: {topic}",
        f"- Mode: {mode}{kind_suffix}",
        f"- Goal: {goal}",
        f"- Core message: {core_message}",
        "- Must-read before finalizing: `consensus.md / research.md / storyboard.md / handoff.md / sources/bridge_briefing.md / strategist_seed.md`",
        "",
        "## IX. Content Outline Starter",
        "",
        *(storyboard_lines or ["- 使用 `storyboard.md` 作为页纲基线补齐正式内容大纲。"]),
        "",
    ]
    return "\n".join(lines)


def _render_spec_lock_starter(project_path: Path) -> str:
    project_info = get_project_info(str(project_path))
    canvas_key = str(project_info.get("format", "ppt169"))
    canvas_info = CANVAS_FORMATS.get(canvas_key, CANVAS_FORMATS["ppt169"])
    lines = [
        "# Spec Lock Starter",
        "",
        "> Starter only. 这是 `Eight Confirmations` 前的锁定草稿，不是正式 `spec_lock.md`，Executor 不能拿它当最终执行合同。",
        "",
        "## canvas",
        f"- viewBox: {canvas_info['viewbox']}",
        f"- format: {canvas_info['name']}",
        "",
        "## colors",
        "- bg: TO_BE_CONFIRMED",
        "- primary: TO_BE_CONFIRMED",
        "- accent: TO_BE_CONFIRMED",
        "- secondary_accent: TO_BE_CONFIRMED",
        "- text: TO_BE_CONFIRMED",
        "- text_secondary: TO_BE_CONFIRMED",
        "- border: TO_BE_CONFIRMED",
        "",
        "## typography",
        "- font_family: TO_BE_CONFIRMED",
        "- title_family: TO_BE_CONFIRMED",
        "- body_family: TO_BE_CONFIRMED",
        "- emphasis_family: TO_BE_CONFIRMED",
        "- code_family: TO_BE_CONFIRMED",
        "- body: TO_BE_CONFIRMED",
        "- title: TO_BE_CONFIRMED",
        "- subtitle: TO_BE_CONFIRMED",
        "- annotation: TO_BE_CONFIRMED",
        "",
        "## notes",
        "- Use `strategist_seed.md` to complete Eight Confirmations before copying into formal `spec_lock.md`.",
        "",
    ]
    return "\n".join(lines)


def _write_downstream_starters(project_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    manifest = _load_bridge_manifest(project_path)
    design_spec_starter = project_path / "design_spec_starter.md"
    spec_lock_starter = project_path / "spec_lock_starter.md"
    design_spec_starter.write_text(_render_design_spec_starter(project_path, manifest), encoding="utf-8")
    spec_lock_starter.write_text(_render_spec_lock_starter(project_path), encoding="utf-8")
    statuses = {
        "ppt_design_spec_starter": _status_entry("written"),
        "ppt_spec_lock_starter": _status_entry("written"),
    }
    artifacts = {
        "design_spec_starter": str(design_spec_starter),
        "spec_lock_starter": str(spec_lock_starter),
    }
    return statuses, artifacts


def _write_downstream_confirmations(project_path: Path) -> Path:
    strategist_seed = project_path / "strategist_seed.md"
    bridge_brief = project_path / "sources" / "bridge_briefing.md"
    manifest = _load_bridge_manifest(project_path)
    topic = str(manifest.get("topic", project_path.name)).strip() or project_path.name
    audience = str(manifest.get("audience", "待确认")).strip() or "待确认"
    goal = str(manifest.get("goal", "待确认")).strip() or "待确认"
    core_message = str(manifest.get("core_message", "待确认")).strip() or "待确认"
    lines = [
        "# Downstream Confirmations",
        "",
        "> 这是给用户直接确认或修改的确认包。它基于 `strategist_seed.md` 压缩整理，但不替代正式 Eight Confirmations 流程。",
        "",
        "## 当前主题",
        "",
        f"- Topic: {topic}",
        f"- Audience: {audience}",
        f"- Goal: {goal}",
        f"- Core message: {core_message}",
        "",
        "## 建议先读",
        "",
        f"- `{bridge_brief}`",
        f"- `{strategist_seed}`",
        "",
        "## 请逐项确认",
        "",
        "1. Canvas format",
        "2. Page count range",
        "3. Target audience",
        "4. Style objective",
        "5. Color scheme",
        "6. Icon usage approach",
        "7. Typography plan",
        "8. Image usage approach",
        "",
        "## 使用方式",
        "",
        "- 如果建议基本对，直接按这 8 项确认后进入正式 `design_spec.md / spec_lock.md`。",
        "- 如果有偏差，优先改这里，再回写正式 spec。",
        "- 不要把这份文件当成最终执行合同。",
        "",
    ]
    path = project_path / "downstream_confirmations.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_downstream_readiness(run_dir: Path, project_path: Path, readiness: dict[str, Any]) -> Path:
    missing = readiness.get("missing_required", [])
    lines = [
        "# Downstream Readiness",
        "",
        "## 当前阻塞原因",
        "",
        "- `full` 需要的下游前置还没齐。",
        "",
        "## 缺失项",
    ]
    if missing:
        lines.extend(f"- `{item}`" for item in missing)
    else:
        lines.append("- 无")
    lines.extend(
        [
            "",
            "## 需要补的文件",
            "",
            f"- `design_spec.md` -> {readiness['required']['design_spec']}",
            f"- `spec_lock.md` -> {readiness['required']['spec_lock']}",
            f"- `svg_output/` -> {readiness['required']['svg_output']}",
            "",
            "## 下一步",
            "",
            "1. 先回到 `ppt-master` 补齐设计稿和锁定稿。",
            "2. 确认 `svg_output/` 已生成。",
            "3. 再重新跑 `render_ppt_output.py --stage full`。",
            "",
            f"## 当前项目",
            "",
            f"- `{project_path}`",
            "",
        ]
    )
    path = run_dir / "downstream_readiness.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _downstream_readiness(project_path: Path) -> dict[str, Any]:
    required = {
        "design_spec": project_path / "design_spec.md",
        "spec_lock": project_path / "spec_lock.md",
        "svg_output": project_path / "svg_output",
    }
    optional = {
        "total_md": project_path / "total.md",
        "notes_dir": project_path / "notes",
    }
    missing_required = [name for name, path in required.items() if not path.exists()]
    readiness = {
        "required": {name: str(path) for name, path in required.items()},
        "optional": {name: str(path) for name, path in optional.items()},
        "missing_required": missing_required,
        "has_total_md": optional["total_md"].exists(),
        "has_notes_dir": optional["notes_dir"].exists(),
    }
    return readiness


def _run_full_export(run_dir: Path, project_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str], str]:
    readiness = _downstream_readiness(project_path)
    statuses: dict[str, dict[str, Any]] = {
        "ppt_bridge_upstream": _status_entry("written"),
    }
    artifacts: dict[str, str] = {}

    seed_statuses, seed_artifacts = _prepare_downstream_seed(project_path)
    statuses.update(seed_statuses)
    artifacts.update(seed_artifacts)
    kickoff_path = _write_downstream_kickoff(project_path)
    statuses["ppt_downstream_kickoff"] = _status_entry("written")
    artifacts["downstream_kickoff"] = str(kickoff_path)
    starter_statuses, starter_artifacts = _write_downstream_starters(project_path)
    statuses.update(starter_statuses)
    artifacts.update(starter_artifacts)
    confirmations_path = _write_downstream_confirmations(project_path)
    statuses["ppt_downstream_confirmations"] = _status_entry("written")
    artifacts["downstream_confirmations"] = str(confirmations_path)

    if readiness["missing_required"]:
        blocked_doc = _write_downstream_readiness(run_dir, project_path, readiness)
        reason = (
            "missing downstream prerequisites: "
            + ", ".join(readiness["missing_required"])
            + "; full stage needs design_spec.md, spec_lock.md, svg_output/"
        )
        statuses["ppt_master_full"] = _status_entry(
            "blocked",
            reason=reason,
            code="missing_downstream_prerequisites",
            details={
                "missing_required": readiness["missing_required"],
                "required": readiness["required"],
            },
        )
        artifacts["downstream_readiness"] = str(blocked_doc)
        return statuses, artifacts, "当前只完成了 bridge 上游包；下游导出被阻塞，先补 design_spec.md / spec_lock.md / svg_output。"

    total_md = project_path / "total.md"
    notes_dir = project_path / "notes"
    if total_md.exists():
        split_result = _run_step([sys.executable, str(TOTAL_MD_SPLIT), str(project_path)], ROOT)
        if split_result.returncode != 0:
            reason = (split_result.stderr or split_result.stdout or "").strip() or "total_md_split failed"
            statuses["ppt_notes_split"] = _status_entry(
                "failed",
                reason=reason,
                code="speaker_notes_split_failed",
            )
            statuses["ppt_master_full"] = _status_entry(
                "blocked",
                reason="speaker notes split failed",
                code="speaker_notes_split_failed",
            )
            return statuses, artifacts, "bridge 上游已完成，但下游在拆 speaker notes 这一步失败。"
        statuses["ppt_notes_split"] = _status_entry("written")
    elif notes_dir.exists():
        statuses["ppt_notes_split"] = _status_entry(
            "skipped",
            reason="notes/ already exists; total.md not provided",
            code="notes_already_present",
        )
    else:
        statuses["ppt_notes_split"] = _status_entry(
            "skipped",
            reason="no total.md and no notes/; continue without speaker notes",
            code="notes_not_provided",
        )

    finalize_result = _run_step([sys.executable, str(FINALIZE_SVG), str(project_path)], ROOT)
    if finalize_result.returncode != 0:
        reason = (finalize_result.stderr or finalize_result.stdout or "").strip() or "finalize_svg failed"
        statuses["ppt_svg_finalize"] = _status_entry(
            "failed",
            reason=reason,
            code="svg_finalize_failed",
        )
        statuses["ppt_master_full"] = _status_entry(
            "blocked",
            reason="svg finalize failed",
            code="svg_finalize_failed",
        )
        return statuses, artifacts, "bridge 上游已完成，但下游在 SVG 后处理这一步失败。"
    statuses["ppt_svg_finalize"] = _status_entry("written")

    before_pptx = _newest_pptx(project_path)
    export_result = _run_step([sys.executable, str(SVG_TO_PPTX), str(project_path)], ROOT)
    if export_result.returncode != 0:
        reason = (export_result.stderr or export_result.stdout or "").strip() or "svg_to_pptx failed"
        statuses["ppt_export"] = _status_entry(
            "failed",
            reason=reason,
            code="ppt_export_failed",
        )
        statuses["ppt_master_full"] = _status_entry(
            "blocked",
            reason="ppt export failed",
            code="ppt_export_failed",
        )
        return statuses, artifacts, "bridge 上游已完成，但下游在 PPTX 导出这一步失败。"

    after_pptx = _newest_pptx(project_path)
    exported_path = after_pptx if after_pptx and after_pptx != before_pptx else after_pptx
    statuses["ppt_export"] = _status_entry("written")
    statuses["ppt_master_full"] = _status_entry("written")
    if exported_path:
        artifacts["pptx"] = str(exported_path)
    return statuses, artifacts, "当前已完成 bridge 上游包，并继续导出了最终 pptx。"


def _write_request_summary(run_dir: Path, args: argparse.Namespace, project_path: Path) -> Path:
    lines = [
        "# PPT Output Request",
        "",
        f"- Topic: {args.topic}",
        f"- Audience: {args.audience or '待补充'}",
        f"- Preset: {args.preset or 'custom'}",
        f"- Goal: {args.goal or '先生成可进入 ppt-master 的上游交接包'}",
        f"- Core message: {args.core_message or args.topic}",
        f"- Stage: {args.stage}",
        f"- Mode: {args.mode}",
        f"- Research kind: {args.research_kind if args.mode == 'research-deck' else 'n/a'}",
        f"- Scope: {args.scope or '聚焦当前主题最小闭环'}",
        f"- Language: {args.language}",
        f"- Page count: {args.page_count}",
        f"- Project path: {project_path}",
    ]
    if args.research_route:
        lines.append(f"- Research route override: {args.research_route}")
    lines.extend(
        [
            "",
            "## Expected Bridge Outputs",
            "",
            "- `consensus.md`",
            "- `research.md`",
            "- `storyboard.md`",
            "- `handoff.md`",
            "- `bridge_manifest.json`",
            "",
        ]
    )
    path = run_dir / "request.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    args = _apply_preset(parse_args())
    _ensure_bridge_exists()
    run_dir = create_run_dir(args.outdir, args.topic)

    project_path = _resolve_project_path(args)
    project_path, created = _ensure_project(project_path)
    _run_upstream(project_path, args)
    request_summary = _write_request_summary(run_dir, args, project_path)

    statuses: dict[str, dict[str, Any]] = {
        "ppt_bridge_upstream": _status_entry("written"),
    }
    downstream_artifacts: dict[str, str] = {}
    next_step = "当前已完成上游 bridge 交接包；如需继续出 PPT，再进入 ppt-master 下游。"
    if args.stage == "full":
        statuses, downstream_artifacts, next_step = _run_full_export(run_dir, project_path)

    output = {
        "run_dir": str(run_dir),
        "tool": "ppt-master-bridge",
        "output_type": "ppt-upstream-package",
        "stage": args.stage,
        "preset": args.preset,
        "mode": args.mode,
        "research_kind": args.research_kind if args.mode == "research-deck" else "",
        "project_path": str(project_path),
        "created_project": created,
        "request_summary": str(request_summary),
        "artifacts": {
            "consensus": str(project_path / "consensus.md"),
            "research": str(project_path / "research.md"),
            "storyboard": str(project_path / "storyboard.md"),
            "handoff": str(project_path / "handoff.md"),
            "manifest": str(project_path / "bridge_manifest.json"),
            **downstream_artifacts,
        },
        "statuses": statuses,
        "request": {
            "topic": args.topic,
            "audience": args.audience,
            "preset": args.preset,
            "goal": args.goal or "先生成可进入 ppt-master 的上游交接包",
            "core_message": args.core_message or args.topic,
            "stage": args.stage,
            "mode": args.mode,
            "research_kind": args.research_kind if args.mode == "research-deck" else "",
            "scope": args.scope or "聚焦当前主题最小闭环",
            "language": args.language,
            "page_count": args.page_count,
            "research_route": args.research_route,
        },
        "next_step": next_step,
        "delivery_note": {
            "formal_artifacts": ["ppt_bridge_upstream", *(["pptx"] if "pptx" in downstream_artifacts else [])],
            "advice": (
                "当前已纳入 bridge 上游包；当 stage=full 且下游条件满足时，也会记录最终 pptx。"
                if args.stage == "full"
                else "当前 output-layer 对 PPT 的接入默认停在 bridge 上游交接包；如需继续出 pptx，请使用 --stage full。"
            ),
        },
    }
    manifest_path = write_manifest(run_dir, output)

    print(f"run_dir={run_dir}")
    print(f"manifest={manifest_path}")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
