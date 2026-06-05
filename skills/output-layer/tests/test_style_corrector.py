from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
import types


SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
for candidate in [str(SRC_ROOT), str(SCRIPTS_ROOT)]:
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from style_corrector import apply_style_correction  # type: ignore


def _import_render_markdown_output():
    fake_pandoc_renderer = types.ModuleType("pandoc_renderer")
    fake_pandoc_renderer.render_docx = lambda *args, **kwargs: (None, "docx renderer not available in test")
    fake_pandoc_renderer.render_pdf = lambda *args, **kwargs: (None, "pdf renderer not available in test")
    sys.modules.setdefault("pandoc_renderer", fake_pandoc_renderer)
    import render_markdown_output  # type: ignore
    return render_markdown_output


class StyleCorrectorTest(unittest.TestCase):
    def test_apply_style_correction_rewrites_explainer_prefix(self) -> None:
        text = "需要注意的是，这件事真正值得问的问题，不是工具好不好用。"
        corrected, meta = apply_style_correction(
            text,
            {"enabled": "on", "preset": "explainer-zh-v1"},
            str(SKILL_ROOT / "profiles" / "style-correction"),
        )
        self.assertIn("真正的问题不是工具好不好用。", corrected)
        self.assertNotIn("需要注意的是", corrected)
        self.assertTrue(meta["changed"])
        self.assertEqual(meta["preset"], "explainer-zh-v1")
        self.assertIsInstance(meta["findings"], list)

    def test_apply_style_correction_uses_preset_finding_rules(self) -> None:
        text = "需要注意的是，先看这个现象。\n\n也就是说，问题还没有说清楚。"
        _, explainer_meta = apply_style_correction(
            text,
            {"enabled": "on", "preset": "explainer-zh-v1"},
            str(SKILL_ROOT / "profiles" / "style-correction"),
        )
        _, business_meta = apply_style_correction(
            text,
            {"enabled": "on", "preset": "business-commentary-zh-v1"},
            str(SKILL_ROOT / "profiles" / "style-correction"),
        )

        explainer_judgment = [
            finding for finding in explainer_meta["findings"] if finding["kind"] == "weak_explicit_judgment"
        ][0]
        business_judgment = [
            finding for finding in business_meta["findings"] if finding["kind"] == "weak_explicit_judgment"
        ][0]

        self.assertEqual(explainer_judgment["severity"], "low")
        self.assertEqual(business_judgment["severity"], "medium")
        self.assertIn("商业判断", business_judgment["message"])

    def test_apply_style_correction_allows_profile_finding_overrides(self) -> None:
        text = "需要注意的是，先看这个现象。"
        _, meta = apply_style_correction(
            text,
            {
                "enabled": "on",
                "preset": "plain-explainer-zh-v1",
                "findings": {
                    "weak_opener": {
                        "severity": "high",
                        "message": "profile override",
                    }
                },
            },
            str(SKILL_ROOT / "profiles" / "style-correction"),
        )

        weak_opener = [finding for finding in meta["findings"] if finding["kind"] == "weak_opener"][0]
        self.assertEqual(weak_opener["severity"], "high")
        self.assertEqual(weak_opener["message"], "profile override")

    def test_render_markdown_output_writes_corrected_artifact(self) -> None:
        render_markdown_output = _import_render_markdown_output()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text("# 标题\n\n需要注意的是，这件事真正值得问的问题，不是工具好不好用。", encoding="utf-8")

            argv = [
                "render_markdown_output.py",
                str(source),
                "--profile",
                "formal-zh",
                "--to",
                "markdown",
                "--outdir",
                str(root / "runs"),
            ]

            with mock.patch.object(sys, "argv", argv):
                exit_code = render_markdown_output.main()

            self.assertEqual(exit_code, 0)
            run_dir = next((root / "runs").iterdir())
            corrected = (run_dir / "output.corrected.md").read_text(encoding="utf-8")
            clean = (run_dir / "output.clean.md").read_text(encoding="utf-8")
            self.assertIn("真正的问题不是工具好不好用。", corrected)
            self.assertIn("真正的问题不是工具好不好用。", clean)
            self.assertNotIn("需要注意的是", clean)

    def test_render_markdown_output_report_only_writes_report_and_skips_downstream(self) -> None:
        render_markdown_output = _import_render_markdown_output()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text(
                "# 标题\n\n需要注意的是，这件事真正值得问的问题，不是工具好不好用。\n\n换句话说，我们可以理解为先看判断。",
                encoding="utf-8",
            )

            argv = [
                "render_markdown_output.py",
                str(source),
                "--profile",
                "formal-zh",
                "--to",
                "markdown,obsidian,docx,pdf",
                "--style-correction-report",
                "only",
                "--outdir",
                str(root / "runs"),
            ]

            with mock.patch.object(sys, "argv", argv):
                exit_code = render_markdown_output.main()

            self.assertEqual(exit_code, 0)
            run_dir = next((root / "runs").iterdir())
            self.assertTrue((run_dir / "output.corrected.md").exists())
            self.assertTrue((run_dir / "style_correction_report.json").exists())
            self.assertFalse((run_dir / "output.clean.md").exists())

            report = json.loads((run_dir / "style_correction_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["style_correction"]["preset"], "explainer-zh-v1")
            self.assertIn("findings", report["style_correction"])

            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["style_correction_report_mode"], "only")
            self.assertEqual(manifest["statuses"]["markdown"]["status"], "skipped")
            self.assertEqual(manifest["statuses"]["obsidian"]["status"], "skipped")
            self.assertEqual(manifest["statuses"]["docx"]["status"], "skipped")
            self.assertEqual(manifest["statuses"]["pdf"]["status"], "skipped")
            self.assertEqual(manifest["statuses"]["style_correction_report"]["status"], "written")
            self.assertEqual(manifest["statuses"]["style_correction_report_md"]["status"], "written")

    def test_render_markdown_output_report_contains_summary_and_sorted_findings(self) -> None:
        render_markdown_output = _import_render_markdown_output()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text(
                "# 标题\n\n需要注意的是，某种程度上这件事还没说清楚。需要注意的是，我们先看现象。换句话说，还是先看现象。",
                encoding="utf-8",
            )

            argv = [
                "render_markdown_output.py",
                str(source),
                "--profile",
                "formal-zh",
                "--to",
                "markdown",
                "--style-correction-report",
                "only",
                "--outdir",
                str(root / "runs"),
            ]

            with mock.patch.object(sys, "argv", argv):
                exit_code = render_markdown_output.main()

            self.assertEqual(exit_code, 0)
            run_dir = next((root / "runs").iterdir())
            report = json.loads((run_dir / "style_correction_report.json").read_text(encoding="utf-8"))
            style_correction = report["style_correction"]
            report_md = (run_dir / "style_correction_report.md").read_text(encoding="utf-8")

            self.assertIn("summary", style_correction)
            self.assertGreaterEqual(style_correction["summary"]["count"], 1)
            self.assertIn("next_actions", style_correction["summary"])
            self.assertEqual(style_correction["findings"][0]["kind"], "weak_opener")
            self.assertIn("Style Correction Report", report_md)
            self.assertIn("Next Actions", report_md)
            self.assertIn("weak_opener", report_md)


if __name__ == "__main__":
    unittest.main()
