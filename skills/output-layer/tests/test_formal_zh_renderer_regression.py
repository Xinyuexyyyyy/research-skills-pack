from __future__ import annotations

import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SKILL_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from markdown_renderer import render_markdown_body


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
RULES = {"numbering": {"level1_style": "chinese", "level2_style": "arabic"}}


class FormalZhMarkdownRendererRegressionTest(unittest.TestCase):
    def _render(self, name: str) -> str:
        text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
        return render_markdown_body(text, RULES)

    def test_core_fixture_promotes_sections_and_separates_blocks(self) -> None:
        rendered = self._render("formal-zh-core.md")

        self.assertIn("# 一、系统概况", rendered)
        self.assertIn("# 二、Agents（3个活跃）", rendered)
        self.assertIn("# 三、存储架构（KO - Knowledge Object系统）", rendered)
        self.assertIn("\n\n- 默认agent使用 `kimi-coding` 为主模型", rendered)
        self.assertIn("\n\n> 生成时间：2026-04-29", rendered)
        self.assertIn("\n\n> 扫描目标：userysys@100.113.27.115 (Tailscale)", rendered)
        self.assertIn("```yaml", rendered)
        self.assertIn("persist_directory: ko_vector_db", rendered)

    def test_structure_fixture_keeps_nested_lists_quotes_tables_and_code(self) -> None:
        rendered = self._render("formal-zh-structure.md")

        self.assertIn("# 一、一级结构", rendered)
        self.assertIn("# 二、二级结构", rendered)
        self.assertIn("## 1. 三级标题样例", rendered)
        self.assertIn("  - 二级列表 A1", rendered)
        self.assertIn("    - 三级列表 A1a", rendered)
        self.assertIn("\n> 引用一\n\n> 引用二", rendered)
        self.assertIn("| 列A | 列B |", rendered)
        self.assertIn("```text", rendered)

