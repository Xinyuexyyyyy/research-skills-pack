from __future__ import annotations

from pathlib import Path
from typing import Any


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any], str | None]] = [(0, data, None)]

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()

        container = stack[-1][1]
        if line.startswith("- "):
            if isinstance(container, list):
                container.append(line[2:].strip())
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value:
            if isinstance(container, dict):
                container[key] = value
                stack[-1] = (stack[-1][0], container, key)
        else:
            next_container: dict[str, Any] | list[Any]
            next_container = {}
            if isinstance(container, dict):
                container[key] = next_container
                stack.append((indent + 2, next_container, key))

    # fix simple list nodes declared as empty maps for defaults.outputs
    defaults = data.get("defaults")
    if isinstance(defaults, dict):
        outputs = defaults.get("outputs")
        if isinstance(outputs, dict) and not outputs:
            defaults["outputs"] = []
    return data


def resolve_profile(profile_name: str, profiles_dir: str) -> dict[str, Any]:
    path = Path(profiles_dir) / f"{profile_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_name}")
    return _read_simple_yaml(path)


def resolve_render_plan(document: dict[str, Any], profile: dict[str, Any], outputs_arg: str | None) -> dict[str, Any]:
    frontmatter = document.get("frontmatter", {})
    requested_outputs: list[str] = []

    if outputs_arg:
        requested_outputs = [item.strip() for item in outputs_arg.split(",") if item.strip()]
    else:
        fm_outputs = frontmatter.get("outputs")
        if isinstance(fm_outputs, list):
            requested_outputs = fm_outputs
        elif isinstance(fm_outputs, str) and fm_outputs:
            requested_outputs = [item.strip() for item in fm_outputs.split(",") if item.strip()]

    defaults = profile.get("defaults", {})
    if not requested_outputs:
        default_outputs = defaults.get("outputs", [])
        if isinstance(default_outputs, list):
            requested_outputs = default_outputs

    if not requested_outputs:
        requested_outputs = ["markdown", "obsidian"]

    return {
        "profile_name": profile.get("name", "unknown"),
        "requested_outputs": requested_outputs,
        "rules": profile.get("rules", {}),
        "obsidian": profile.get("obsidian", {}),
        "docx": profile.get("docx", {}),
        "style_correction": profile.get("style_correction", {}),
        "frontmatter": frontmatter,
    }
