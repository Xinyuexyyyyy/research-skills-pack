from __future__ import annotations

import json
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path.cwd()
SCRIPT = SKILL_ROOT / "scripts" / "render_markdown_output.py"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
RULES = "总标题黑体小二，正文仿宋GB2312小四，一级标题依赖正文，字体加粗，一级标题字号三号，段落规则固定28磅，非标题正文首行缩进2字符，标题段前空10磅段后空14磅，一级标题用一、二、三、，二级标题用1. 2. 3.，页码启用"
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _docx_rows(docx_path: Path) -> list[dict[str, str | int | None]]:
    rows: list[dict[str, str | int | None]] = []
    with ZipFile(docx_path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    for paragraph in root.findall(".//w:body/w:p", WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
        ppr = paragraph.find("w:pPr", WORD_NS)
        style = None
        level: int | None = None
        if ppr is not None:
            pstyle = ppr.find("w:pStyle", WORD_NS)
            if pstyle is not None:
                style = pstyle.attrib.get(f"{{{WORD_NS['w']}}}val")
            numpr = ppr.find("w:numPr", WORD_NS)
            if numpr is not None:
                ilvl = numpr.find("w:ilvl", WORD_NS)
                if ilvl is not None:
                    level = int(ilvl.attrib.get(f"{{{WORD_NS['w']}}}val", "0"))
        rows.append({"text": text, "style": style, "level": level})
    return rows


def _docx_table_count(docx_path: Path) -> int:
    with ZipFile(docx_path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    return len(root.findall(".//w:tbl", WORD_NS))


class RenderMarkdownOutputRegressionTest(unittest.TestCase):
    def _run_renderer(self, input_path: Path, outputs: str = "markdown,docx") -> Path:
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir, ignore_errors=True)
        outdir = Path(temp_dir) / "runs"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(input_path),
                "--profile",
                "formal-zh",
                "--to",
                outputs,
                "--rules",
                RULES,
                "--outdir",
                str(outdir),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        run_dir = None
        for line in result.stdout.splitlines():
            if line.startswith("run_dir="):
                run_dir = Path(line.split("=", 1)[1].strip())
                break
        self.assertIsNotNone(run_dir, result.stdout)
        return run_dir

    def test_sample_source_smoke(self) -> None:
        run_dir = self._run_renderer(SKILL_ROOT / "samples" / "source.md")
        self.assertTrue((run_dir / "output.clean.md").exists())
        self.assertTrue((run_dir / "output.docx").exists())
        self.assertTrue((run_dir / "index.md").exists())

        payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["statuses"]["markdown"]["status"], "written")
        self.assertEqual(payload["statuses"]["docx"]["status"], "written")
        self.assertEqual(payload["docx_reference"]["mode"], "generated")
        self.assertTrue((run_dir / "formal-zh-reference.docx").exists())

        index_text = (run_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("clean markdown", index_text)
        self.assertIn("manifest.json", index_text)

        rows = _docx_rows(run_dir / "output.docx")
        self.assertEqual(rows[0]["style"], "Title")
        self.assertTrue(any(row["style"] == "Heading2" and row["text"] == "1. 二级标题样例" for row in rows))

    def test_core_fixture_docx_matches_formal_rules(self) -> None:
        run_dir = self._run_renderer(FIXTURES_DIR / "formal-zh-core.md")
        clean_text = (run_dir / "output.clean.md").read_text(encoding="utf-8")
        self.assertIn("# 一、系统概况", clean_text)
        self.assertIn("# 二、Agents (3 个活跃)", clean_text)
        self.assertIn("\n\n- 默认 agent 使用 `kimi-coding` 为主模型", clean_text)
        self.assertIn("\n\n> 生成时间：2026-04-29", clean_text)

        payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("总标题改为黑体小二", payload["rule_override_notes"])
        self.assertIn("首行缩进改为两字符", payload["rule_override_notes"])

        rows = _docx_rows(run_dir / "output.docx")
        self.assertIn({"text": "生成时间：2026-04-29", "style": "BlockText", "level": None}, rows)
        self.assertIn({"text": "扫描目标：userysys@100.113.27.115 (Tailscale)", "style": "BlockText", "level": None}, rows)
        self.assertTrue(any(row["text"].endswith("系统概况") and row["style"] == "Heading1" for row in rows))
        self.assertTrue(any(row["text"] == "模型路由配置：" and row["style"] == "BodyText" for row in rows))
        self.assertTrue(any(row["text"] == "默认 agent 使用 kimi-coding 为主模型" and row["style"] == "Compact" and row["level"] == 0 for row in rows))
        self.assertTrue(any(row["style"] == "SourceCode" and "storage:" in row["text"] for row in rows))

    def test_structure_fixture_covers_nested_lists_tables_quotes_and_code(self) -> None:
        run_dir = self._run_renderer(FIXTURES_DIR / "formal-zh-structure.md")
        clean_text = (run_dir / "output.clean.md").read_text(encoding="utf-8")
        self.assertIn("# 一、一级结构", clean_text)
        self.assertIn("# 二、二级结构", clean_text)
        self.assertIn("## 1. 三级标题样例", clean_text)
        self.assertIn("  - 二级列表 A1", clean_text)
        self.assertIn("    - 三级列表 A1a", clean_text)
        self.assertIn("\n> 引用一\n\n> 引用二", clean_text)
        self.assertIn("```text", clean_text)

        rows = _docx_rows(run_dir / "output.docx")
        self.assertEqual(_docx_table_count(run_dir / "output.docx"), 1)
        levels = sorted({row["level"] for row in rows if row["level"] is not None})
        self.assertIn(0, levels)
        self.assertIn(1, levels)
        self.assertTrue(any(row["style"] in {"BlockText", "Quote"} and row["text"] == "引用一" for row in rows))
        self.assertTrue(any(row["style"] == "SourceCode" and row["text"].startswith("line 1") for row in rows))

    def test_formal_report_sample_uses_all_default_outputs(self) -> None:
        run_dir = self._run_renderer(SKILL_ROOT / "samples" / "formal-report.md", "markdown,obsidian,docx,pdf")
        payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["statuses"]["markdown"]["status"], "written")
        self.assertEqual(payload["statuses"]["docx"]["status"], "written")
        self.assertEqual(payload["statuses"]["pdf"]["status"], "written")
        self.assertTrue((run_dir / "output.pdf").exists())
        self.assertTrue((run_dir / "output.docx").exists())

    def test_default_docx_uses_shared_reference_template(self) -> None:
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir, ignore_errors=True)
        outdir = Path(temp_dir) / "runs"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(SKILL_ROOT / "samples" / "formal-report.md"),
                "--profile",
                "formal-zh",
                "--to",
                "markdown,docx",
                "--outdir",
                str(outdir),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        run_dir = None
        for line in result.stdout.splitlines():
            if line.startswith("run_dir="):
                run_dir = Path(line.split("=", 1)[1].strip())
                break
        self.assertIsNotNone(run_dir, result.stdout)

        payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["docx_reference"]["mode"], "template")
        self.assertTrue(payload["docx_reference"]["path"].endswith("templates/docx/formal-zh-reference.docx"))
        self.assertTrue((run_dir / "formal-zh-reference.docx").exists())
        self.assertTrue((run_dir / "output.docx").exists())

    def test_meeting_note_sample_keeps_short_form_readable(self) -> None:
        run_dir = self._run_renderer(SKILL_ROOT / "samples" / "meeting-note.md")
        clean_text = (run_dir / "output.clean.md").read_text(encoding="utf-8")
        self.assertIn("# 会议纪要样例", clean_text)
        self.assertIn("已确认输出层主链", clean_text)
        self.assertIn("已确认 PDF 后端使用本机 weasyprint", clean_text)
