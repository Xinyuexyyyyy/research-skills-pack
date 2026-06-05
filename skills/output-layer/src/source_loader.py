from __future__ import annotations

from pathlib import Path
from typing import Any


def _parse_simple_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    end_marker = "\n---\n"
    end = text.find(end_marker, 4)
    if end == -1:
        return {}, text

    raw = text[4:end].splitlines()
    body = text[end + len(end_marker) :]
    data: dict[str, Any] = {}
    current_key: str | None = None

    for line in raw:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key:
            data.setdefault(current_key, [])
            data[current_key].append(stripped[2:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        if value:
            data[current_key] = value
        else:
            data[current_key] = []

    return data, body


def load_markdown(source_path: str) -> dict[str, Any]:
    path = Path(source_path).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_simple_frontmatter(text)
    return {
        "source_path": str(path),
        "frontmatter": frontmatter,
        "body": body,
        "raw_text": text,
    }
