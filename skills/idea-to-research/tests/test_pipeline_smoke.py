from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys

# 测试运行要求：必须在技能根目录下运行
# 通过向上 1 层定位到技能根目录（tests/ -> idea-to-research/）
SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from idea_to_research.pipeline import (
    build_idea_brief,
    build_research_prompt,
    build_route_decision,
    continue_session,
    export_session,
    run_pipeline,
    start_session,
)


class PipelineSmokeTest(unittest.TestCase):
    def test_align_returns_clarification_for_ambiguous_request(self) -> None:
        request = "我有个新想法，先帮我看看下一步怎么研究比较合适"
        route = build_route_decision(request)
        self.assertEqual(route.route, "needs-clarification")
        self.assertIn("待澄清", route.route_label)
        self.assertEqual(route.confidence, "低")

    def test_align_prefers_github_build_for_harvest_request(self) -> None:
        request = "想抄 GitHub 上成熟的 skill，后面直接接开发实现"
        route = build_route_decision(request)
        self.assertEqual(route.route, "github-build")
        self.assertIn("GitHub 借鉴", route.route_label)

    def test_align_prefers_product_research_for_feature_request(self) -> None:
        request = "我有个新功能想法，想先定义用户、需求和 MVP，再决定做不做"
        route = build_route_decision(request)
        self.assertEqual(route.route, "product-research")

    def test_build_prompt_uses_route_specific_framework(self) -> None:
        request = "我有个新功能想法，想先定义用户、需求和 MVP，再决定做不做"
        brief = build_idea_brief(request)
        route = build_route_decision(request)
        prompt = build_research_prompt(brief, route)
        self.assertIn("产品发现", prompt.framework)

    def test_build_idea_brief_extracts_primary_user_hint_from_transform_request(self) -> None:
        request = "我想做一个帮远程团队把 Slack 和飞书里的零散反馈沉成可执行产品需求的工具，先帮我做产品调研"
        brief = build_idea_brief(request)
        self.assertEqual(brief.primary_user_hint, "远程团队里的 PM、产品负责人或项目负责人")
        self.assertIn("Slack 和飞书里的零散反馈", brief.core_problem)
        self.assertNotIn("先帮我做产品调研", brief.core_problem)

    def test_run_pipeline_non_github_route_skips_harvest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            result = run_pipeline(
                request="我想做一个面向年轻人的新产品，先帮我定义问题和目标用户",
                output_root=output_root,
                now=datetime(2026, 5, 13, 17, 0, 0),
            )
            report_dir = output_root / "idea-to-research-20260513-170000"
            self.assertEqual(result["route"], "product-research")
            self.assertTrue((report_dir / "route-decision.md").exists())
            self.assertTrue((report_dir / "idea-brief.md").exists())
            self.assertTrue((report_dir / "research-prompt.md").exists())
            self.assertTrue((report_dir / "candidates.md").exists())
            self.assertTrue((report_dir / "product-route.md").exists())
            self.assertTrue((report_dir / "product-research-brief.md").exists())
            self.assertTrue((report_dir / "problem-statement.md").exists())
            self.assertTrue((report_dir / "validation-plan.md").exists())
            self.assertTrue((report_dir / "final-report.md").exists())
            self.assertEqual(result["selected_repos"], [])
            payload = json.loads((report_dir / "consensus.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["route"], "product-research")

    def test_run_pipeline_social_route_writes_full_social_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            result = run_pipeline(
                request="我想研究年轻人为什么越来越抗拒职场升职，这更像社会趋势还是分群差异，先帮我做社会调研",
                output_root=output_root,
                now=datetime(2026, 5, 16, 20, 0, 0),
            )
            report_dir = output_root / "idea-to-research-20260516-200000"
            self.assertEqual(result["route"], "social-research")
            self.assertTrue((report_dir / "social-route.md").exists())
            self.assertTrue((report_dir / "social-research-brief.md").exists())
            self.assertTrue((report_dir / "research-scope.md").exists())
            self.assertTrue((report_dir / "population-or-case-definition.md").exists())
            self.assertTrue((report_dir / "evidence-log.md").exists())
            self.assertTrue((report_dir / "uncertainty-and-bias.md").exists())
            self.assertTrue((report_dir / "reader-brief.md").exists())
            self.assertTrue((report_dir / "final-report.md").exists())
            payload = json.loads((report_dir / "consensus.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["route"], "social-research")
            self.assertEqual(result["harvest_consensus_title"], payload["title"])

    def test_run_pipeline_ambiguous_request_stays_in_clarification_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            result = run_pipeline(
                request="我有个新想法，先帮我看看下一步怎么研究比较合适",
                output_root=output_root,
                now=datetime(2026, 5, 16, 20, 5, 0),
            )
            report_dir = output_root / "idea-to-research-20260516-200500"
            self.assertEqual(result["route"], "needs-clarification")
            self.assertTrue((report_dir / "clarification-brief.md").exists())
            self.assertFalse((report_dir / "product-route.md").exists())
            self.assertFalse((report_dir / "social-route.md").exists())
            self.assertFalse((report_dir / "github-build-brief.md").exists())
            payload = json.loads((report_dir / "consensus.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["route"], "needs-clarification")

    def test_run_pipeline_accepts_structured_search_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            def fake_search(query: str, count: int):
                return {
                    "status": "ok",
                    "errors": [],
                    "warnings": [],
                    "repos": [
                        {
                            "name": "demo/repo",
                            "description": "demo repo",
                            "url": "https://github.com/demo/repo",
                            "stars": 42,
                            "language": "Python",
                            "last_commit": "2026-05-14",
                        }
                    ],
                }

            def fake_harvest(url: str, repo_name: str):
                return {
                    "project": repo_name,
                    "url": url,
                    "readme": {"raw": "demo"},
                    "structure": {"root_files": ["README.md"], "directories": ["src"]},
                    "code_files": {"files": []},
                }

            result = run_pipeline(
                request="想抄 GitHub 上成熟的 skill，后面直接接开发实现",
                output_root=output_root,
                search_fn=fake_search,
                harvest_fn=fake_harvest,
                now=datetime(2026, 5, 14, 10, 0, 0),
            )
            self.assertEqual(result["route"], "github-build")
            self.assertEqual(result["selected_repos"], ["demo/repo"])

    def test_session_flow_can_clarify_and_export_product_research(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session = start_session(
                request="我有个新想法，想做个把聊天反馈整理成需求的东西，先帮我看看怎么研究",
                output_root=root / "sessions",
                now=datetime(2026, 5, 16, 21, 0, 0),
            )
            self.assertEqual(session["route"], "product-research")
            session_dir = Path(session["session_dir"])
            self.assertTrue((session_dir / "session.json").exists())

            continued = continue_session(
                session_dir=session_dir,
                reply="\n".join(
                    [
                        "路线：产品调研",
                        "目标用户：远程团队里的 PM、产品负责人或项目负责人",
                        "当前做法：今天主要靠 Slack、飞书、文档和表格手动整理",
                        "重点：先验证需求和用户场景",
                    ]
                ),
                now=datetime(2026, 5, 16, 21, 5, 0),
            )
            self.assertEqual(continued["route"], "product-research")
            self.assertEqual(continued["stage"], "research-ready")

            exported = export_session(
                session_dir=session_dir,
                output_root=root / "consensus",
                slug="session-export-check",
                now=datetime(2026, 5, 16, 21, 10, 0),
            )
            report_dir = root / "consensus" / "session-export-check"
            self.assertEqual(exported["route"], "product-research")
            self.assertTrue((report_dir / "product-route.md").exists())
            self.assertTrue((session_dir / "export-summary.json").exists())
            final_report = (report_dir / "final-report.md").read_text(encoding="utf-8")
            problem_statement = (report_dir / "problem-statement.md").read_text(encoding="utf-8")
            product_route = (report_dir / "product-route.md").read_text(encoding="utf-8")
            reader_brief = (report_dir / "reader-brief.md").read_text(encoding="utf-8")
            target_user = (report_dir / "target-user.md").read_text(encoding="utf-8")
            self.assertIn("聊天反馈", final_report)
            self.assertNotIn("先验证需求和用户场景", final_report)
            self.assertNotIn("待确认", final_report)
            self.assertNotIn("workaround", final_report)
            self.assertIn("需求草稿", final_report)
            self.assertIn("这轮标题", final_report)
            self.assertIn("把聊天反馈整理成需求草稿", final_report)
            self.assertIn("项目标题", final_report)
            self.assertIn("聊天反馈需求整理", final_report)
            self.assertIn("一句话问题定义", final_report)
            self.assertIn("更快整理成需求草稿", final_report)
            self.assertNotIn("手动整理手动处理", final_report)
            self.assertNotIn("聊天反馈 -> 可执行需求", final_report)
            self.assertNotIn("可执行需求", final_report)
            self.assertIn("远程团队里的 PM、产品负责人或项目负责人", final_report)
            self.assertIn("Slack、飞书、文档和表格手动整理", problem_statement)
            self.assertNotIn("Core problem", problem_statement)
            self.assertNotIn("Current alternatives", problem_statement)
            self.assertIn("把聊天反馈整理成需求草稿", product_route)
            self.assertNotIn("内部主题", product_route)
            self.assertNotIn("内部标识", product_route)
            self.assertIn("一句话问题定义", reader_brief)
            self.assertIn("远程团队里的 PM、产品负责人或项目负责人", target_user)
            self.assertNotIn("待确认", target_user)
            self.assertNotIn("Primary user", target_user)

    def test_session_export_preserves_github_theme_after_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session = start_session(
                request="我想做个把零散产品想法收成 PRD 草稿的 skill，先帮我看看怎么研究",
                output_root=root / "sessions",
                now=datetime(2026, 5, 16, 21, 15, 0),
            )
            session_dir = Path(session["session_dir"])

            continued = continue_session(
                session_dir=session_dir,
                reply="\n".join(
                    [
                        "路线：github-build",
                        "目标：重点抄实现方式和目录结构",
                        "复用方式：改造复用",
                        "后续动作：后面准备直接接开发",
                    ]
                ),
                now=datetime(2026, 5, 16, 21, 20, 0),
            )
            self.assertEqual(continued["route"], "github-build")
            self.assertEqual(continued["stage"], "research-ready")

            def fake_search(query: str, count: int):
                return {
                    "status": "ok",
                    "errors": [],
                    "warnings": [],
                    "repos": [
                        {
                            "name": "demo/prd-skill",
                            "description": "Turn ideas into PRD drafts",
                            "url": "https://github.com/demo/prd-skill",
                            "stars": 12,
                            "language": "Python",
                            "last_commit": "2026-05-14",
                        }
                    ],
                }

            def fake_harvest(url: str, repo_name: str):
                return {
                    "project": repo_name,
                    "url": url,
                    "readme": {"raw": "demo"},
                    "structure": {"root_files": ["README.md"], "directories": ["src"]},
                    "code_files": {"files": []},
                }

            exported = export_session(
                session_dir=session_dir,
                output_root=root / "consensus",
                slug="github-theme-check",
                search_fn=fake_search,
                harvest_fn=fake_harvest,
                now=datetime(2026, 5, 16, 21, 25, 0),
            )
            self.assertEqual(exported["route"], "github-build")
            brief = (root / "consensus" / "github-theme-check" / "github-build-brief.md").read_text(encoding="utf-8")
            self.assertIn("零散产品想法 -> PRD 草稿", brief)
            self.assertNotIn("后面准备直接接开发", brief)


if __name__ == "__main__":
    unittest.main()
