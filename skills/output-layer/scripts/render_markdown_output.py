#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from artifact_writer import create_run_dir, write_manifest
from markdown_renderer import render_clean_markdown
from obsidian_renderer import render_obsidian
from pandoc_renderer import render_docx, render_pdf
from profile_resolver import resolve_profile, resolve_render_plan
from rule_overrides import apply_rule_overrides
from source_loader import load_markdown
from style_corrector import apply_style_correction
from zhlint_processor import run_zhlint_fix


def _render_style_correction_report_markdown(report_payload: dict) -> str:
    style = report_payload.get("style_correction", {}) if isinstance(report_payload.get("style_correction"), dict) else {}
    summary = style.get("summary", {}) if isinstance(style.get("summary"), dict) else {}
    findings = style.get("findings", []) if isinstance(style.get("findings"), list) else []
    next_actions = summary.get("next_actions", []) if isinstance(summary.get("next_actions"), list) else []

    lines: list[str] = [
        "# Style Correction Report",
        "",
        f"- Source: {report_payload.get('source_path', '')}",
        f"- Profile: {report_payload.get('profile', '')}",
        f"- Preset: {style.get('preset', '')}",
        f"- Enabled: {style.get('enabled', False)}",
        f"- Changed: {style.get('changed', False)}",
        "",
        "## Summary",
        "",
        f"- Findings: {summary.get('count', 0)}",
        f"- Top issue: {summary.get('top_kind', '') or 'none'}",
        f"- Top severity: {summary.get('top_severity', '') or 'none'}",
    ]

    if next_actions:
        lines.extend(["", "## Next Actions", ""])
        lines.extend(f"- {action}" for action in next_actions)

    lines.extend(["", "## Findings", ""])
    if findings:
        for index, finding in enumerate(findings, start=1):
            lines.append(f"### {index}. {finding.get('kind', 'unknown')}")
            lines.append("")
            lines.append(f"- Severity: {finding.get('severity', '')}")
            lines.append(f"- Message: {finding.get('message', '')}")
            if finding.get("sample"):
                lines.append(f"- Sample: {finding.get('sample')}")
            details = finding.get("details")
            if isinstance(details, list) and details:
                detail_text = ", ".join(
                    f"{item.get('phrase', '')} x{item.get('count', '')}" for item in details if isinstance(item, dict)
                )
                lines.append(f"- Details: {detail_text}")
            lines.append("")
    else:
        lines.append("- No findings.")
        lines.append("")

    lines.extend(["## Applied Rewrites", ""])
    notes = style.get("applied_notes", []) if isinstance(style.get("applied_notes"), list) else []
    if notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("- No rewrites applied.")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render confirmed Markdown into output-layer artifacts.")
    parser.add_argument("input", help="Markdown source path")
    parser.add_argument("--profile", default="formal-zh", help="Profile name")
    parser.add_argument("--to", default="", help="Comma-separated outputs, e.g. markdown,obsidian,docx,pdf")
    parser.add_argument("--rules", default="", help="Natural-language rule overrides, e.g. '宋体小四，1.5倍行距，首行缩进两字符'")
    parser.add_argument("--style-correction", default="", help="Style correction preset override: auto/off/<preset>")
    parser.add_argument("--style-correction-report", default="", help="Style correction report mode: only")
    parser.add_argument("--template", default="", help="Preset docx template: formal-zh, formal-zh-no-number, academic-zh, memo-zh")
    parser.add_argument("--outdir", default=str(ROOT / "output" / "output-layer"), help="Output base directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    document = load_markdown(args.input)
    profile = resolve_profile(args.profile, str(Path(__file__).resolve().parents[1] / "profiles"))
    plan = resolve_render_plan(document, profile, args.to or None)
    resolved_rules, rule_notes = apply_rule_overrides(plan["rules"], args.rules)
    plan["rules"] = resolved_rules
    run_dir = create_run_dir(args.outdir, document["source_path"])

    style_config = dict(plan.get("style_correction", {}) or {})
    if args.style_correction:
        override = args.style_correction.strip()
        if override.lower() == "off":
            style_config["enabled"] = "off"
        elif override.lower() == "auto":
            style_config["enabled"] = "on"
        else:
            style_config["enabled"] = "on"
            style_config["preset"] = override

    corrected_body, style_meta = apply_style_correction(
        document["body"],
        style_config,
        str(Path(__file__).resolve().parents[1] / "profiles" / "style-correction"),
    )

    source_copy = run_dir / "source.md"
    source_copy.write_text(document["raw_text"], encoding="utf-8")
    corrected_path = run_dir / "output.corrected.md"
    corrected_path.write_text(corrected_body, encoding="utf-8")

    # B path: zhlint auto-fix
    zhlint_body, zhlint_report = run_zhlint_fix(corrected_body, run_dir)
    zhlint_path = run_dir / "output.zhlint.md"
    zhlint_path.write_text(zhlint_body, encoding="utf-8")
    zhlint_report_path = run_dir / "zhlint_report.json"
    zhlint_report_path.write_text(json.dumps(zhlint_report, ensure_ascii=False, indent=2), encoding="utf-8")

    report_mode = args.style_correction_report.strip().lower()
    report_only = report_mode == "only"
    report_path = run_dir / "style_correction_report.json"
    report_payload = {
        "source_path": document["source_path"],
        "profile": plan["profile_name"],
        "style_correction": style_meta,
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path = run_dir / "style_correction_report.md"
    report_md_path.write_text(_render_style_correction_report_markdown(report_payload), encoding="utf-8")

    artifacts: dict[str, str] = {}
    statuses: dict[str, dict[str, str]] = {}
    docx_reference_meta = {"mode": "none", "path": ""}
    artifacts["source"] = str(source_copy)
    artifacts["style_corrected"] = str(corrected_path)
    statuses["style_corrected"] = {"status": "written" if style_meta.get("enabled") else "skipped"}
    artifacts["style_correction_report"] = str(report_path)
    artifacts["style_correction_report_md"] = str(report_md_path)
    statuses["style_correction_report"] = {"status": "written"}
    statuses["style_correction_report_md"] = {"status": "written"}
    artifacts["zhlint"] = str(zhlint_path)
    artifacts["zhlint_report"] = str(zhlint_report_path)
    statuses["zhlint"] = {"status": zhlint_report.get("status", "unknown")}
    statuses["zhlint_report"] = {"status": "written"}

    clean_path = None
    if report_only:
        for output_name in ["markdown", "obsidian", "docx", "pdf"]:
            if output_name in plan["requested_outputs"]:
                statuses[output_name] = {"status": "skipped", "reason": "style_correction_report_only"}
    elif "markdown" in plan["requested_outputs"]:
        clean_path = render_clean_markdown(zhlint_body, run_dir, plan["rules"])
        artifacts["markdown"] = str(clean_path)
        statuses["markdown"] = {"status": "written"}

    if not report_only and "obsidian" in plan["requested_outputs"]:
        input_for_obsidian = clean_path or render_clean_markdown(zhlint_body, run_dir, plan["rules"])
        obsidian_path, err = render_obsidian(input_for_obsidian, run_dir, ROOT, plan["obsidian"].get("mode", "obsidian-enhanced"))
        if obsidian_path:
            artifacts["obsidian"] = str(obsidian_path)
            statuses["obsidian"] = {"status": "written"}
        else:
            statuses["obsidian"] = {"status": "failed", "reason": err or "unknown error"}

    if not report_only and "docx" in plan["requested_outputs"]:
        input_for_docx = clean_path or render_clean_markdown(zhlint_body, run_dir, plan["rules"])
        reference_doc = None

        # A path: preset template selection
        template_override = args.template.strip()
        if template_override:
            preset_path = Path(__file__).resolve().parents[1] / "templates" / "docx" / f"{template_override}.docx"
            if preset_path.exists():
                reference_doc = run_dir / f"{template_override}-reference.docx"
                shutil.copy2(preset_path, reference_doc)
                docx_reference_meta = {"mode": "preset", "preset": template_override, "path": str(preset_path)}

        # Fallback to profile-based template
        if reference_doc is None:
            reference_name = plan.get("docx", {}).get("reference_doc")
            if reference_name:
                reference_doc = run_dir / reference_name
                template_reference = Path(__file__).resolve().parents[1] / "templates" / "docx" / reference_name
                if template_reference.exists() and not args.rules.strip():
                    shutil.copy2(template_reference, reference_doc)
                    docx_reference_meta = {"mode": "template", "path": str(template_reference)}
                else:
                    build_reference = [
                    "python3",
                    str(Path(__file__).resolve().parents[0] / "build_reference_doc.py"),
                    "--body-font",
                    plan["rules"].get("typography", {}).get("body_font", "宋体"),
                    "--body-size",
                    plan["rules"].get("typography", {}).get("body_size", "小四"),
                    "--title-font",
                    plan["rules"].get("typography", {}).get("title_font", "黑体"),
                    "--title-size",
                    plan["rules"].get("typography", {}).get("title_size", "小二"),
                    "--title-weight",
                    plan["rules"].get("typography", {}).get("title_weight", "bold"),
                    "--title-align",
                    plan["rules"].get("typography", {}).get("title_align", "center"),
                    "--heading-font",
                    plan["rules"].get("typography", {}).get("heading_font", "黑体"),
                    "--heading-weight",
                    plan["rules"].get("typography", {}).get("heading_weight", "bold"),
                    "--heading1-size",
                    str(plan["rules"].get("typography", {}).get("heading1_size", "16")),
                    "--heading2-size",
                    str(plan["rules"].get("typography", {}).get("heading2_size", "14")),
                    "--heading3-size",
                    str(plan["rules"].get("typography", {}).get("heading3_size", "12")),
                    "--line-spacing",
                    str(plan["rules"].get("paragraph", {}).get("line_spacing", "28")),
                    "--first-line-indent",
                    plan["rules"].get("paragraph", {}).get("first_line_indent", "2char"),
                    "--spacing-before",
                    str(plan["rules"].get("paragraph", {}).get("spacing_before", "0")),
                    "--spacing-after",
                    str(plan["rules"].get("paragraph", {}).get("spacing_after", "0")),
                    "--alignment",
                    str(plan["rules"].get("paragraph", {}).get("alignment", "justify")),
                    "--heading1-spacing-before",
                    str(plan["rules"].get("headings", {}).get("heading1_spacing_before", "12")),
                    "--heading1-spacing-after",
                    str(plan["rules"].get("headings", {}).get("heading1_spacing_after", "6")),
                    "--heading2-spacing-before",
                    str(plan["rules"].get("headings", {}).get("heading2_spacing_before", "10")),
                    "--heading2-spacing-after",
                    str(plan["rules"].get("headings", {}).get("heading2_spacing_after", "6")),
                    "--heading3-spacing-before",
                    str(plan["rules"].get("headings", {}).get("heading3_spacing_before", "8")),
                    "--heading3-spacing-after",
                    str(plan["rules"].get("headings", {}).get("heading3_spacing_after", "3")),
                    "--heading-align",
                    str(plan["rules"].get("headings", {}).get("heading_align", "left")),
                    "--margin",
                    plan["rules"].get("page", {}).get("margin", "normal"),
                    "--top-margin",
                    str(plan["rules"].get("page", {}).get("top_margin", "")),
                    "--bottom-margin",
                    str(plan["rules"].get("page", {}).get("bottom_margin", "")),
                    "--left-margin",
                    str(plan["rules"].get("page", {}).get("left_margin", "")),
                    "--right-margin",
                    str(plan["rules"].get("page", {}).get("right_margin", "")),
                    "--page-number",
                    plan["rules"].get("page", {}).get("page_number", "off"),
                    "--page-number-align",
                    plan["rules"].get("page", {}).get("page_number_align", "center"),
                    "--first-page-number",
                    plan["rules"].get("page", {}).get("first_page_number", "off"),
                    "--header-text",
                    plan["rules"].get("page", {}).get("header_text", ""),
                    "--footer-text",
                    plan["rules"].get("page", {}).get("footer_text", ""),
                    "--header-align",
                    plan["rules"].get("page", {}).get("header_align", "center"),
                    "--footer-align",
                    plan["rules"].get("page", {}).get("footer_align", "center"),
                    "--header-font",
                    plan["rules"].get("page", {}).get("header_font", "宋体"),
                    "--header-size",
                    str(plan["rules"].get("page", {}).get("header_size", "小五")),
                    "--footer-font",
                    plan["rules"].get("page", {}).get("footer_font", "宋体"),
                    "--footer-size",
                    str(plan["rules"].get("page", {}).get("footer_size", "小五")),
                    "--page-number-font",
                    plan["rules"].get("page", {}).get("page_number_font", "宋体"),
                    "--page-number-size",
                    str(plan["rules"].get("page", {}).get("page_number_size", "小五")),
                        "--output",
                        str(reference_doc),
                    ]
                    import subprocess
                    subprocess.run(build_reference, check=True, capture_output=True, text=True)
                    docx_reference_meta = {"mode": "generated", "path": str(reference_doc)}
        docx_path, err = render_docx(input_for_docx, run_dir, reference_doc)
        if docx_path:
            if reference_doc and reference_doc.exists():
                artifacts["docx_reference"] = str(reference_doc)
            artifacts["docx"] = str(docx_path)
            statuses["docx"] = {"status": "written"}
        else:
            statuses["docx"] = {"status": "blocked", "reason": err or "unknown error"}

    if not report_only and "pdf" in plan["requested_outputs"]:
        input_for_pdf = clean_path or render_clean_markdown(zhlint_body, run_dir)
        pdf_path, err = render_pdf(input_for_pdf, run_dir)
        if pdf_path:
            artifacts["pdf"] = str(pdf_path)
            statuses["pdf"] = {"status": "written"}
        else:
            statuses["pdf"] = {"status": "blocked", "reason": err or "unknown error"}

    index_path = run_dir / "index.md"
    manifest_path = run_dir / "manifest.json"
    artifacts["index"] = str(index_path)
    artifacts["manifest"] = str(manifest_path)

    manifest = {
        "source_path": document["source_path"],
        "profile": plan["profile_name"],
        "requested_outputs": plan["requested_outputs"],
        "artifacts": artifacts,
        "statuses": statuses,
        "rules": plan["rules"],
        "rule_override_notes": rule_notes,
        "style_correction": style_meta,
        "style_correction_report_mode": report_mode or "off",
        "docx_reference": docx_reference_meta if "docx" in plan["requested_outputs"] else {"mode": "none", "path": ""},
        "obsidian_mode": plan["obsidian"].get("mode", "obsidian-enhanced"),
        "delivery_note": {
            "formal_artifacts": [key for key in ["docx", "obsidian", "markdown", "pdf"] if key in artifacts],
            "advice": "当前第一版正式主链是 markdown / obsidian / docx；如果某个格式失败，请以 statuses 中的具体 reason 为准。"
        },
    }
    manifest_path = write_manifest(run_dir, manifest)
    index_lines = [
        "# output-layer run index",
        "",
        f"- source: `source.md`",
        f"- style corrected: `output.corrected.md`",
    ]
    if "markdown" in artifacts:
        index_lines.append("- clean markdown: `output.clean.md`")
    if "obsidian" in artifacts:
        index_lines.append("- obsidian: `output.obsidian.md`")
    if "docx" in artifacts:
        index_lines.append("- docx: `output.docx`")
    if "pdf" in artifacts:
        index_lines.append("- pdf: `output.pdf`")
    index_lines.extend(
        [
            "- style correction report json: `style_correction_report.json`",
            "- style correction report markdown: `style_correction_report.md`",
            "- manifest: `manifest.json`",
            "",
            "## Statuses",
            "",
        ]
    )
    for name, info in statuses.items():
        reason = f" ({info['reason']})" if info.get("reason") else ""
        index_lines.append(f"- `{name}`: {info['status']}{reason}")
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    print(f"run_dir={run_dir}")
    print(f"manifest={manifest_path}")
    for name, info in statuses.items():
        reason = f" ({info['reason']})" if info.get("reason") else ""
        print(f"{name}: {info['status']}{reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
