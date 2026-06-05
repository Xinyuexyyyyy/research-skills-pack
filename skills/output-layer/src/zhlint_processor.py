"""zhlint integration for output-layer.

Run zhlint --fix on corrected markdown to auto-fix Chinese typography issues
(Chinese-English spacing, full/half-width punctuation, etc.).

Produces:
- output.zhlint.md : fixed markdown text
- zhlint_report.json : validation report with counts
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def run_zhlint_fix(
    text: str,
    run_dir: Path,
) -> tuple[str, dict]:
    """Run zhlint --fix on text, return (fixed_text, report).

    If zhlint is not installed, return original text with a skip report.
    """
    if not shutil.which("zhlint"):
        return text, {
            "status": "skipped",
            "reason": "zhlint not installed",
            "findings": 0,
            "fixed": False,
        }

    input_path = run_dir / "_zhlint_input.md"
    output_path = run_dir / "output.zhlint.md"
    input_path.write_text(text, encoding="utf-8")

    # zhlint requires relative paths, so run from run_dir
    rel_input = "_zhlint_input.md"

    try:
        # First run lint to get report (without --fix)
        report_result = subprocess.run(
            ["zhlint", rel_input],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(run_dir),
        )
        has_errors = report_result.returncode != 0

        # Then run fix
        fix_result = subprocess.run(
            ["zhlint", "--fix", rel_input],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(run_dir),
        )

        fixed_text = input_path.read_text(encoding="utf-8")
        output_path.write_text(fixed_text, encoding="utf-8")

        report = {
            "status": "fixed" if has_errors else "clean",
            "findings": has_errors,
            "fixed": has_errors,
            "stdout": report_result.stdout.strip() if has_errors else "",
            "stderr": report_result.stderr.strip() if report_result.stderr else "",
        }

        return fixed_text, report

    except subprocess.TimeoutExpired:
        return text, {
            "status": "timeout",
            "reason": "zhlint timed out after 30s",
            "findings": 0,
            "fixed": False,
        }
    except Exception as exc:
        return text, {
            "status": "error",
            "reason": str(exc),
            "findings": 0,
            "fixed": False,
        }
