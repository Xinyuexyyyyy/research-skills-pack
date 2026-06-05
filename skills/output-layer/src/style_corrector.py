from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from profile_resolver import resolve_profile


DELETE_TOKEN = "<DELETE>"
DEFAULT_FINDING_RULES = {
    "weak_opener": {
        "prefixes": (
            "需要注意的是，",
            "值得注意的是，",
            "某种程度上，",
            "从某种意义上说，",
            "说到底，",
            "归根结底，",
        ),
        "severity": "medium",
        "message": "开头先用了套话，结论起得偏慢。",
    },
    "repeated_template_phrases": {
        "phrases": (
            "需要注意的是",
            "值得注意的是",
            "某种程度上",
            "从某种意义上说",
            "换句话说",
            "归根结底",
        ),
        "threshold": 2,
        "severity": "medium",
        "message": "模板化表达重复出现，容易带出 AI 味。",
    },
    "weak_explicit_judgment": {
        "markers": (
            "我的判断是",
            "我判断",
            "核心是",
            "关键是",
            "关键不是",
            "真正的问题",
            "问题在于",
            "本质上",
            "更准确地说",
        ),
        "severity": "low",
        "message": "正文里缺少明确判断句，容易只解释现象，不落判断。",
    },
}


def _is_enabled(value: Any) -> bool:
    return str(value or "").strip().lower() in {"on", "true", "1", "yes", "auto"}


def _normalize_replacement(value: Any) -> str:
    if str(value).strip() == DELETE_TOKEN:
        return ""
    return str(value or "")


def _is_plain_paragraph(block: str) -> bool:
    stripped = block.strip()
    if not stripped:
        return False
    first_line = stripped.splitlines()[0].strip()
    if first_line.startswith(("```", "#", ">", "|", "![", "<!--")):
        return False
    if re.match(r"^(?:[-*+]|(?:\d+[.)]))\s+", first_line):
        return False
    return True


def _apply_prefix_rewrites(block: str, rewrites: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    updated = block
    for source, target in rewrites.items():
        replacement = _normalize_replacement(target)
        if updated.startswith(source):
            updated = replacement + updated[len(source) :]
            notes.append(f"prefix:{source}->{replacement or 'DELETE'}")
    return updated, notes


def _apply_sentence_rewrites(block: str, rewrites: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    updated = block
    for source, target in rewrites.items():
        replacement = _normalize_replacement(target)
        if source in updated:
            updated = updated.replace(source, replacement)
            notes.append(f"sentence:{source}->{replacement or 'DELETE'}")
    return updated, notes


def _cleanup_spacing(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def _split_csv_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    text = str(value or "").strip()
    if not text:
        return ()
    return tuple(item.strip() for item in text.split(",") if item.strip())


def _merge_finding_rules(
    base_rules: dict[str, Any] | None,
    custom_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    base = base_rules or {}
    custom = custom_rules or {}
    for kind, defaults in DEFAULT_FINDING_RULES.items():
        merged[kind] = dict(defaults)
        if isinstance(base.get(kind), dict):
            merged[kind].update(base[kind])
        if isinstance(custom.get(kind), dict):
            merged[kind].update(custom[kind])
    return merged


def _severity_rank(severity: Any) -> int:
    value = str(severity or "").strip().lower()
    return {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }.get(value, 4)


def _finding_rank(kind: Any) -> int:
    value = str(kind or "").strip()
    return {
        "weak_opener": 0,
        "weak_explicit_judgment": 1,
        "repeated_template_phrases": 2,
    }.get(value, 9)


def _summarize_findings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = _sort_findings(findings)
    counts: dict[str, int] = {}
    for finding in ordered:
        kind = str(finding.get("kind", "")).strip() or "unknown"
        counts[kind] = counts.get(kind, 0) + 1
    next_actions: list[str] = []
    if any(item.get("kind") == "weak_explicit_judgment" for item in ordered):
        next_actions.append("先补明确判断句，把结论前移。")
    if any(item.get("kind") == "weak_opener" for item in ordered):
        next_actions.append("先改开头，去掉套话和铺垫。")
    if any(item.get("kind") == "repeated_template_phrases" for item in ordered):
        next_actions.append("再压模板词，减少重复连接句。")
    if not next_actions and ordered:
        next_actions.append("优先处理最高严重度的发现。")
    return {
        "count": len(ordered),
        "by_kind": counts,
        "top_kind": str(ordered[0].get("kind", "")) if ordered else "",
        "top_severity": str(ordered[0].get("severity", "")) if ordered else "",
        "next_actions": next_actions,
    }


def _sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda item: (
            _severity_rank(item.get("severity")),
            _finding_rank(item.get("kind")),
            str(item.get("kind", "")),
        ),
    )


def _collect_findings(body: str, finding_rules: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    stripped = body.strip()
    if not stripped:
        return findings

    weak_opener_cfg = finding_rules.get("weak_opener", {}) if isinstance(finding_rules, dict) else {}
    template_cfg = finding_rules.get("repeated_template_phrases", {}) if isinstance(finding_rules, dict) else {}
    judgment_cfg = finding_rules.get("weak_explicit_judgment", {}) if isinstance(finding_rules, dict) else {}

    blocks = [block.strip() for block in stripped.split("\n\n") if block.strip()]
    first_plain = next((block for block in blocks if _is_plain_paragraph(block)), "")

    if first_plain:
        first_line = first_plain.splitlines()[0].strip()
        prefixes = _split_csv_values(weak_opener_cfg.get("prefixes", ()))
        if _is_enabled(weak_opener_cfg.get("enabled", "on")) and prefixes and any(
            first_line.startswith(prefix) for prefix in prefixes
        ):
            findings.append(
                {
                    "kind": "weak_opener",
                    "severity": str(weak_opener_cfg.get("severity", DEFAULT_FINDING_RULES["weak_opener"]["severity"])),
                    "message": str(weak_opener_cfg.get("message", DEFAULT_FINDING_RULES["weak_opener"]["message"])),
                    "sample": first_line[:80],
                }
            )

    repeated_templates: list[dict[str, Any]] = []
    template_phrases = _split_csv_values(template_cfg.get("phrases", ()))
    threshold = int(template_cfg.get("threshold", DEFAULT_FINDING_RULES["repeated_template_phrases"]["threshold"]))
    for phrase in template_phrases:
        count = body.count(phrase)
        if count >= threshold:
            repeated_templates.append({"phrase": phrase, "count": count})
    if _is_enabled(template_cfg.get("enabled", "on")) and repeated_templates:
        findings.append(
            {
                "kind": "repeated_template_phrases",
                "severity": str(
                    template_cfg.get("severity", DEFAULT_FINDING_RULES["repeated_template_phrases"]["severity"])
                ),
                "message": str(template_cfg.get("message", DEFAULT_FINDING_RULES["repeated_template_phrases"]["message"])),
                "details": repeated_templates,
            }
        )

    judgment_markers = _split_csv_values(judgment_cfg.get("markers", ()))
    if _is_enabled(judgment_cfg.get("enabled", "on")) and judgment_markers and not any(
        marker in body for marker in judgment_markers
    ):
        findings.append(
            {
                "kind": "weak_explicit_judgment",
                "severity": str(
                    judgment_cfg.get("severity", DEFAULT_FINDING_RULES["weak_explicit_judgment"]["severity"])
                ),
                "message": str(
                    judgment_cfg.get("message", DEFAULT_FINDING_RULES["weak_explicit_judgment"]["message"])
                ),
            }
        )

    return findings


def apply_style_correction(
    body: str,
    config: dict[str, Any] | None,
    presets_dir: str,
) -> tuple[str, dict[str, Any]]:
    cfg = config or {}
    if not _is_enabled(cfg.get("enabled")):
        finding_rules = _merge_finding_rules(
            None,
            cfg.get("findings") if isinstance(cfg.get("findings"), dict) else None,
        )
        findings = _sort_findings(_collect_findings(body, finding_rules))
        summary = _summarize_findings(findings)
        return body, {
            "enabled": False,
            "preset": "",
            "spec": cfg.get("spec", ""),
            "applied_notes": [],
            "changed": False,
            "findings": findings,
            "finding_rules": finding_rules,
            "summary": summary,
        }

    preset_name = str(cfg.get("preset") or "explainer-zh-v1").strip()
    preset = resolve_profile(preset_name, presets_dir)
    preset_rules = preset.get("rules", {})
    rewrite_rules = preset.get("rewrites", {})
    preset_findings = preset.get("findings", {}) if isinstance(preset.get("findings", {}), dict) else {}
    profile_findings = cfg.get("findings", {}) if isinstance(cfg.get("findings", {}), dict) else {}
    finding_rules = _merge_finding_rules(preset_findings, profile_findings)
    findings = _sort_findings(_collect_findings(body, finding_rules))
    summary = _summarize_findings(findings)
    prefix_rewrites = rewrite_rules.get("paragraph_prefix", {})
    sentence_rewrites = rewrite_rules.get("sentence", {})

    blocks = body.split("\n\n")
    corrected_blocks: list[str] = []
    applied_notes: list[str] = []

    for block in blocks:
        updated = block
        if _is_plain_paragraph(block):
            if _is_enabled(preset_rules.get("paragraph_prefix_rewrites")) and isinstance(prefix_rewrites, dict):
                updated, notes = _apply_prefix_rewrites(updated, prefix_rewrites)
                applied_notes.extend(notes)
            if _is_enabled(preset_rules.get("sentence_rewrites")) and isinstance(sentence_rewrites, dict):
                updated, notes = _apply_sentence_rewrites(updated, sentence_rewrites)
                applied_notes.extend(notes)
        corrected_blocks.append(updated)

    corrected = "\n\n".join(corrected_blocks)
    if _is_enabled(preset_rules.get("trim_whitespace")):
        corrected = _cleanup_spacing(corrected)
    else:
        corrected = corrected if corrected.endswith("\n") else corrected + "\n"

    changed = corrected != (body if body.endswith("\n") else body + "\n")
    return corrected, {
        "enabled": True,
        "preset": preset_name,
        "spec": cfg.get("spec", ""),
        "applied_notes": applied_notes,
        "changed": changed,
        "findings": findings,
        "finding_rules": finding_rules,
        "summary": summary,
    }
