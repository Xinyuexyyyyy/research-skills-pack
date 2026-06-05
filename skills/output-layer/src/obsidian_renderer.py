from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _resolve_polisher_script(root: Path) -> Path | None:
    candidates = [
        root / "skills" / "output-polisher" / "scripts" / "polish-markdown.js",
        Path(__file__).resolve().parents[2] / "output-polisher" / "scripts" / "polish-markdown.js",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def render_obsidian(input_markdown: Path, run_dir: Path, root: Path, mode: str = "obsidian-enhanced") -> tuple[Path | None, str | None]:
    script = _resolve_polisher_script(root)
    node_bin = shutil.which("node")
    if not script or not node_bin:
        return None, "output-polisher or node not available"

    output_path = run_dir / "output.obsidian.md"
    try:
        subprocess.run(
            [
                node_bin,
                str(script),
                "--mode",
                mode,
                "--input",
                str(input_markdown),
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return None, exc.stderr.strip() or str(exc)
    return output_path, None
