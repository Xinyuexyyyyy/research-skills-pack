from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SKILL_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pandoc_renderer import _resolve_pdf_engine, render_pdf


class PandocRendererPdfTest(unittest.TestCase):
    def test_resolve_pdf_engine_prefers_xelatex(self) -> None:
        def fake_which(name: str) -> str | None:
            mapping = {
                "weasyprint": None,
                "xelatex": "/usr/local/bin/xelatex",
                "lualatex": "/usr/local/bin/lualatex",
                "pandoc": "/usr/local/bin/pandoc",
            }
            return mapping.get(name)

        with mock.patch("pandoc_renderer.shutil.which", side_effect=fake_which):
            self.assertEqual(_resolve_pdf_engine(), ("xelatex", "latex"))

    def test_resolve_pdf_engine_falls_back_to_html_engine(self) -> None:
        def fake_which(name: str) -> str | None:
            mapping = {
                "weasyprint": None,
                "pandoc": "/usr/local/bin/pandoc",
                "wkhtmltopdf": "/usr/local/bin/wkhtmltopdf",
            }
            return mapping.get(name)

        with mock.patch("pandoc_renderer.shutil.which", side_effect=fake_which):
            self.assertEqual(_resolve_pdf_engine(), ("wkhtmltopdf", "html"))

    def test_render_pdf_reports_missing_engine(self) -> None:
        def fake_which(name: str) -> str | None:
            if name == "pandoc":
                return "/usr/local/bin/pandoc"
            return None

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text("# 标题\n\n正文。", encoding="utf-8")
            with mock.patch("pandoc_renderer.shutil.which", side_effect=fake_which):
                output_path, reason = render_pdf(source, root)
            self.assertIsNone(output_path)
            self.assertIsNotNone(reason)
            self.assertIn("no pdf engine found", reason)
            self.assertIn("xelatex", reason)

    def test_render_pdf_uses_html5_for_html_engine(self) -> None:
        def fake_which(name: str) -> str | None:
            mapping = {
                "weasyprint": None,
                "pandoc": "/usr/local/bin/pandoc",
                "wkhtmltopdf": "/usr/local/bin/wkhtmltopdf",
            }
            return mapping.get(name)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text("# 标题\n\n正文。", encoding="utf-8")

            def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
                self.assertIn("--pdf-engine", command)
                self.assertIn("wkhtmltopdf", command)
                self.assertIn("-t", command)
                self.assertIn("html5", command)
                self.assertIn("-s", command)
                (root / "output.pdf").write_bytes(b"%PDF-1.4\n")

                class Result:
                    stdout = ""
                    stderr = ""

                return Result()

            with mock.patch("pandoc_renderer.shutil.which", side_effect=fake_which):
                with mock.patch("pandoc_renderer.subprocess.run", side_effect=fake_run):
                    output_path, reason = render_pdf(source, root)

            self.assertIsNone(reason)
            self.assertEqual(output_path, root / "output.pdf")
            self.assertTrue((root / "output.pdf").exists())

    def test_render_pdf_prefers_weasyprint_cli_when_available(self) -> None:
        def fake_which(name: str) -> str | None:
            mapping = {
                "pandoc": "/usr/local/bin/pandoc",
                "weasyprint": "/opt/homebrew/bin/weasyprint",
            }
            return mapping.get(name)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text("# 标题\n\n正文。", encoding="utf-8")

            with mock.patch("pandoc_renderer.shutil.which", side_effect=fake_which):
                with mock.patch("pandoc_renderer._build_pdf_html", return_value="<html><head></head><body></body></html>") as mock_build:
                    def fake_run(command, check, capture_output, text):
                        self.assertEqual(command[0], "weasyprint")
                        self.assertTrue(command[1].endswith("output.pdf.html"))
                        self.assertTrue(command[2].endswith("output.pdf"))
                        (root / "output.pdf").write_bytes(b"%PDF-1.4\nfake\n")

                        class Result:
                            stdout = ""
                            stderr = ""

                        return Result()

                    with mock.patch("pandoc_renderer.subprocess.run", side_effect=fake_run):
                        output_path, reason = render_pdf(source, root)
                self.assertIsNone(reason)
                self.assertEqual(output_path, root / "output.pdf")
                self.assertTrue((root / "output.pdf").exists())
                mock_build.assert_called_once()

    def test_real_pdf_output_looks_like_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            source.write_text("# 标题\n\n正文。", encoding="utf-8")
            output_path, reason = render_pdf(source, root)
            self.assertIsNone(reason, reason)
            self.assertIsNotNone(output_path)
            assert output_path is not None
            pdf_bytes = output_path.read_bytes()
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))
            self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()
