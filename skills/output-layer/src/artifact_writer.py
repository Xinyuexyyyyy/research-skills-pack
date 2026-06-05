from __future__ import annotations

import json
from itertools import count
from datetime import datetime
from pathlib import Path
from typing import Any


def create_run_dir(base_dir: str, source_path: str) -> Path:
    source_name = Path(source_path).stem or "source"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    base_path = Path(base_dir)
    for suffix in count():
        suffix_text = "" if suffix == 0 else f"-{suffix}"
        run_dir = base_path / f"{timestamp}-{source_name}{suffix_text}"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    return run_dir


def write_manifest(run_dir: Path, payload: dict[str, Any]) -> Path:
    path = run_dir / "manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
