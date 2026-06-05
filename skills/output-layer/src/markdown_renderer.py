from __future__ import annotations

import re
from pathlib import Path
from typing import Any


CN_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def _strip_heading_prefix(text: str) -> str:
    return re.sub(r"^(?:[一二三四五六七八九十]+、|\d+[.、．]\s*|（\d+）\s*|（[一二三四五六七八九十]+）\s*)", "", text).strip()


def _is_list_item(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*+]|(?:\d+[.)]))\s+\S", line))


def _separate_list_blocks(lines: list[str]) -> list[str]:
    separated: list[str] = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            separated.append(line)
            continue
        if not in_code_block and _is_list_item(line):
            prev = next((item for item in reversed(separated) if item.strip()), "")
            if prev and not _is_list_item(prev) and not re.match(r"^\s*\d+[.)]\s+", prev) and not prev.startswith("#") and prev != "---":
                separated.append("")
        separated.append(line)
    return separated


def _is_quote_line(line: str) -> bool:
    return bool(re.match(r"^\s*>\s+\S", line))


def _separate_quote_blocks(lines: list[str]) -> list[str]:
    separated: list[str] = []
    in_code_block = False
    total = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            separated.append(line)
            continue
        if (
            not in_code_block
            and stripped == ">"
            and index > 0
            and index + 1 < total
            and _is_quote_line(lines[index - 1])
            and _is_quote_line(lines[index + 1])
            and (not separated or separated[-1].strip())
        ):
            separated.append("")
            continue
        if not in_code_block and _is_quote_line(line):
            prev = next((item for item in reversed(separated) if item.strip()), "")
            if prev and _is_quote_line(prev):
                separated.append("")
        separated.append(line)
    return separated


def _to_chinese_number(n: int) -> str:
    if 1 <= n <= len(CN_NUMERALS):
        return CN_NUMERALS[n - 1]
    return str(n)


def render_markdown_body(body: str, rules: dict[str, Any] | None = None) -> str:
    rules = rules or {}
    numbering = rules.get("numbering", {})
    level1_style = numbering.get("level1_style", "chinese")
    level2_style = numbering.get("level2_style", "arabic")
    if level1_style == "none" and level2_style == "none":
        return body.strip() + "\n"

    heading_lines = [
        re.match(r"^(#{1,6})\s+(.*)$", raw_line)
        for raw_line in body.strip().splitlines()
    ]
    has_lone_document_title = False
    h1_total = sum(1 for item in heading_lines if item and len(item.group(1)) == 1)
    h2_total = sum(1 for item in heading_lines if item and len(item.group(1)) == 2)
    if h1_total == 1 and h2_total > 0:
        has_lone_document_title = True

    h1_index = 0
    h2_index = 0
    title_seen = False
    rendered: list[str] = []
    for raw_line in body.strip().splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", raw_line)
        if not match:
            rendered.append(raw_line)
            continue
        hashes, title = match.groups()
        level = len(hashes)
        clean_title = _strip_heading_prefix(title)
        if level == 1 and level1_style != "none":
            if not title_seen:
                title_seen = True
                rendered.append(f"{hashes} {clean_title}")
                continue
            h1_index += 1
            prefix = _to_chinese_number(h1_index)
            rendered.append(f"{hashes} {prefix}、{clean_title}")
            continue
        if has_lone_document_title and level == 2 and level1_style != "none":
            h1_index += 1
            h2_index = 0
            prefix = _to_chinese_number(h1_index)
            rendered.append(f"# {prefix}、{clean_title}")
            continue
        if has_lone_document_title and level == 3 and level2_style != "none":
            h2_index += 1
            prefix = f"{h2_index}." if level2_style == "arabic" else _to_chinese_number(h2_index)
            rendered.append(f"## {prefix} {clean_title}".rstrip())
            continue
        if level == 2 and level2_style != "none":
            h2_index += 1
            prefix = f"{h2_index}." if level2_style == "arabic" else _to_chinese_number(h2_index)
            rendered.append(f"{hashes} {prefix} {clean_title}".rstrip())
            continue
        rendered.append(f"{hashes} {clean_title}".rstrip())

    rendered = _separate_quote_blocks(_separate_list_blocks(rendered))
    text = "\n".join(rendered).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text + "\n"


def render_clean_markdown(body: str, run_dir: Path, rules: dict[str, Any] | None = None) -> Path:
    clean_text = render_markdown_body(body, rules)
    path = run_dir / "output.clean.md"
    path.write_text(clean_text, encoding="utf-8")
    return path
