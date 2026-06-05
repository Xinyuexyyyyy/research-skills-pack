from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
from datetime import datetime


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import render_ppt_output  # type: ignore
from artifact_writer import create_run_dir  # type: ignore


class RenderPptOutputSmokeTest(unittest.TestCase):
    def _run_main(self, argv: list[str], fake_project: Path) -> int:
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(render_ppt_output, "_ensure_bridge_exists", return_value=None):
                with mock.patch.object(render_ppt_output, "_ensure_project", return_value=(fake_project, False)):
                    with mock.patch.object(render_ppt_output, "_run_upstream", return_value=None):
                        return render_ppt_output.main()

    def _run_main_with_real_upstream(self, argv: list[str], fake_project: Path) -> int:
        return self._run_main(argv, fake_project)

    def test_main_writes_run_dir_request_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_project = root / "fake-ppt-project"
            fake_project.mkdir(parents=True, exist_ok=True)

            argv = [
                "render_ppt_output.py",
                "--topic",
                "本科生怎么写专利",
                "--audience",
                "本科生",
                "--goal",
                "先生成可进入 ppt-master 的上游交接包",
                "--core-message",
                "先把为什么写专利、什么是专利、怎么写清楚",
                "--mode",
                "research-deck",
                "--research-kind",
                "intro-share",
                "--outdir",
                str(root / "runs"),
                "--project-path",
                str(fake_project),
            ]
            exit_code = self._run_main(argv, fake_project)

            self.assertEqual(exit_code, 0)

            run_dirs = list((root / "runs").iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            request_md = run_dir / "request.md"
            manifest_json = run_dir / "manifest.json"

            self.assertTrue(request_md.exists())
            self.assertTrue(manifest_json.exists())

            request_text = request_md.read_text(encoding="utf-8")
            self.assertIn("本科生怎么写专利", request_text)
            self.assertIn("intro-share", request_text)
            self.assertIn(str(fake_project), request_text)

            payload = json.loads(manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["tool"], "ppt-master-bridge")
            self.assertEqual(payload["output_type"], "ppt-upstream-package")
            self.assertEqual(payload["project_path"], str(fake_project))
            self.assertEqual(payload["request"]["topic"], "本科生怎么写专利")
            self.assertEqual(payload["request"]["research_kind"], "intro-share")
            self.assertEqual(payload["statuses"]["ppt_bridge_upstream"]["status"], "written")
            self.assertEqual(payload["request_summary"], str(request_md))
            self.assertEqual(payload["artifacts"]["storyboard"], str(fake_project / "storyboard.md"))
            self.assertEqual(payload["artifacts"]["manifest"], str(fake_project / "bridge_manifest.json"))

    def test_preset_pitch_applies_default_mode_goal_and_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_project = root / "fake-ppt-project"
            fake_project.mkdir(parents=True, exist_ok=True)

            argv = [
                "render_ppt_output.py",
                "--topic",
                "AI 助手路演",
                "--preset",
                "pitch",
                "--outdir",
                str(root / "runs"),
                "--project-path",
                str(fake_project),
            ]
            exit_code = self._run_main(argv, fake_project)

            self.assertEqual(exit_code, 0)
            run_dir = next((root / "runs").iterdir())
            payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            request_text = (run_dir / "request.md").read_text(encoding="utf-8")

            self.assertEqual(payload["preset"], "pitch")
            self.assertEqual(payload["mode"], "pitch-deck")
            self.assertEqual(payload["request"]["preset"], "pitch")
            self.assertEqual(payload["request"]["goal"], "先生成对外说服型 PPT 上游交接包")
            self.assertEqual(payload["request"]["page_count"], 10)
            self.assertEqual(payload["request"]["research_kind"], "")
            self.assertIn("- Preset: pitch", request_text)

    def test_preset_does_not_override_explicit_mode_fields(self) -> None:
        argv = [
            "render_ppt_output.py",
            "--topic",
            "本科生怎么写专利",
            "--preset",
            "pitch",
            "--mode",
            "research-deck",
            "--research-kind",
            "intro-share",
            "--page-count",
            "12",
            "--goal",
            "用户自定义目标",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = render_ppt_output._apply_preset(render_ppt_output.parse_args())

        self.assertEqual(args.preset, "pitch")
        self.assertEqual(args.mode, "research-deck")
        self.assertEqual(args.research_kind, "intro-share")
        self.assertEqual(args.page_count, 12)
        self.assertEqual(args.goal, "用户自定义目标")

    def test_create_run_dir_avoids_collision_when_called_in_same_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixed_now = datetime(2026, 5, 20, 10, 32, 21, 123456)

            with mock.patch("artifact_writer.datetime") as mock_datetime:
                mock_datetime.now.return_value = fixed_now
                first = create_run_dir(str(root), "本科生怎么写专利")
                second = create_run_dir(str(root), "本科生怎么写专利")

            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertIn("20260520-103221-123456", first.name)
            self.assertIn("20260520-103221-123456", second.name)
            self.assertNotEqual(first.name, second.name)

    def test_main_full_stage_marks_blocked_when_downstream_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_project = root / "fake-ppt-project"
            fake_project.mkdir(parents=True, exist_ok=True)

            argv = [
                "render_ppt_output.py",
                "--topic",
                "本科生怎么写专利",
                "--stage",
                "full",
                "--outdir",
                str(root / "runs"),
                "--project-path",
                str(fake_project),
            ]
            seed_statuses = {
                "ppt_bridge_brief": {"status": "written", "code": "ok", "reason": ""},
                "ppt_strategist_seed": {"status": "written", "code": "ok", "reason": ""},
            }
            seed_artifacts = {
                "bridge_briefing": str(fake_project / "sources" / "bridge_briefing.md"),
                "strategist_seed": str(fake_project / "strategist_seed.md"),
            }
            (fake_project / "sources").mkdir(parents=True, exist_ok=True)
            (fake_project / "sources" / "bridge_briefing.md").write_text("# brief", encoding="utf-8")
            (fake_project / "strategist_seed.md").write_text("# seed", encoding="utf-8")
            (fake_project / "bridge_manifest.json").write_text(
                json.dumps(
                    {
                        "topic": "本科生怎么写专利",
                        "mode": "research-deck",
                        "research_kind": "intro-share",
                        "audience": "本科生",
                        "goal": "先生成可进入 ppt-master 的上游交接包",
                        "core_message": "先把为什么写专利、什么是专利、怎么写清楚",
                        "page_count": 8,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with mock.patch.object(render_ppt_output, "_prepare_downstream_seed", return_value=(seed_statuses, seed_artifacts)):
                exit_code = self._run_main(argv, fake_project)

            self.assertEqual(exit_code, 0)

            run_dir = next((root / "runs").iterdir())
            payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(payload["stage"], "full")
            self.assertEqual(payload["statuses"]["ppt_bridge_upstream"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_bridge_brief"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_strategist_seed"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_master_full"]["status"], "blocked")
            self.assertEqual(payload["statuses"]["ppt_master_full"]["code"], "missing_downstream_prerequisites")
            self.assertIn("design_spec", payload["statuses"]["ppt_master_full"]["reason"])
            self.assertIn("details", payload["statuses"]["ppt_master_full"])
            self.assertEqual(
                payload["statuses"]["ppt_master_full"]["details"]["missing_required"],
                ["design_spec", "spec_lock", "svg_output"],
            )
            self.assertIn("bridge_briefing", payload["artifacts"])
            self.assertIn("strategist_seed", payload["artifacts"])
            self.assertIn("downstream_kickoff", payload["artifacts"])
            self.assertIn("design_spec_starter", payload["artifacts"])
            self.assertIn("spec_lock_starter", payload["artifacts"])
            self.assertIn("downstream_confirmations", payload["artifacts"])
            self.assertIn("downstream_readiness", payload["artifacts"])
            kickoff_path = Path(payload["artifacts"]["downstream_kickoff"])
            self.assertTrue(kickoff_path.exists())
            kickoff_text = kickoff_path.read_text(encoding="utf-8")
            self.assertIn("Eight Confirmations 清单", kickoff_text)
            self.assertIn("downstream_kickoff.md", kickoff_path.name)
            design_starter_path = Path(payload["artifacts"]["design_spec_starter"])
            spec_starter_path = Path(payload["artifacts"]["spec_lock_starter"])
            confirmations_path = Path(payload["artifacts"]["downstream_confirmations"])
            self.assertTrue(design_starter_path.exists())
            self.assertTrue(spec_starter_path.exists())
            self.assertTrue(confirmations_path.exists())
            self.assertIn("Design Spec Starter", design_starter_path.read_text(encoding="utf-8"))
            self.assertIn("Spec Lock Starter", spec_starter_path.read_text(encoding="utf-8"))
            self.assertIn("Downstream Confirmations", confirmations_path.read_text(encoding="utf-8"))
            readiness_path = Path(payload["artifacts"]["downstream_readiness"])
            self.assertTrue(readiness_path.exists())
            self.assertEqual(readiness_path.parent, run_dir)
            readiness_text = readiness_path.read_text(encoding="utf-8")
            self.assertIn("design_spec.md", readiness_text)
            self.assertIn("spec_lock.md", readiness_text)
            self.assertIn("svg_output/", readiness_text)
            self.assertTrue(Path(payload["artifacts"]["bridge_briefing"]).exists())
            self.assertTrue(Path(payload["artifacts"]["strategist_seed"]).exists())
            self.assertNotIn("pptx", payload["artifacts"])
            self.assertIn("下游导出被阻塞", payload["next_step"])

    def test_main_full_stage_writes_pptx_artifact_when_downstream_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_project = root / "fake-ppt-project"
            fake_project.mkdir(parents=True, exist_ok=True)
            (fake_project / "design_spec.md").write_text("# design", encoding="utf-8")
            (fake_project / "spec_lock.md").write_text("# lock", encoding="utf-8")
            (fake_project / "svg_output").mkdir(parents=True, exist_ok=True)
            (fake_project / "sources").mkdir(parents=True, exist_ok=True)
            (fake_project / "sources" / "bridge_briefing.md").write_text("# brief", encoding="utf-8")
            (fake_project / "strategist_seed.md").write_text("# seed", encoding="utf-8")
            (fake_project / "bridge_manifest.json").write_text(
                json.dumps(
                    {
                        "topic": "本科生怎么写专利",
                        "mode": "research-deck",
                        "research_kind": "intro-share",
                        "audience": "本科生",
                        "goal": "先生成可进入 ppt-master 的上游交接包",
                        "core_message": "先把为什么写专利、什么是专利、怎么写清楚",
                        "page_count": 8,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            exported = fake_project / "exports" / "undergrad-patent-writing_20260520_103232.pptx"

            argv = [
                "render_ppt_output.py",
                "--topic",
                "本科生怎么写专利",
                "--stage",
                "full",
                "--outdir",
                str(root / "runs"),
                "--project-path",
                str(fake_project),
            ]

            success = subprocess.CompletedProcess(args=["mock"], returncode=0, stdout="", stderr="")
            seed_statuses = {
                "ppt_bridge_brief": {"status": "written", "code": "ok", "reason": ""},
                "ppt_strategist_seed": {"status": "written", "code": "ok", "reason": ""},
            }
            seed_artifacts = {
                "bridge_briefing": str(fake_project / "sources" / "bridge_briefing.md"),
                "strategist_seed": str(fake_project / "strategist_seed.md"),
            }
            with mock.patch.object(render_ppt_output, "_prepare_downstream_seed", return_value=(seed_statuses, seed_artifacts)):
                with mock.patch.object(render_ppt_output, "_run_step", side_effect=[success, success]):
                    with mock.patch.object(render_ppt_output, "_newest_pptx", side_effect=[None, exported]):
                        exit_code = self._run_main(argv, fake_project)

            self.assertEqual(exit_code, 0)

            run_dir = next((root / "runs").iterdir())
            payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(payload["stage"], "full")
            self.assertEqual(payload["statuses"]["ppt_notes_split"]["status"], "skipped")
            self.assertEqual(payload["statuses"]["ppt_svg_finalize"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_export"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_master_full"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_master_full"]["code"], "ok")
            self.assertEqual(payload["statuses"]["ppt_downstream_kickoff"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_design_spec_starter"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_spec_lock_starter"]["status"], "written")
            self.assertEqual(payload["statuses"]["ppt_downstream_confirmations"]["status"], "written")
            self.assertIn("downstream_kickoff", payload["artifacts"])
            self.assertIn("design_spec_starter", payload["artifacts"])
            self.assertIn("spec_lock_starter", payload["artifacts"])
            self.assertIn("downstream_confirmations", payload["artifacts"])
            self.assertEqual(payload["artifacts"]["pptx"], str(exported))
            self.assertIn("导出了最终 pptx", payload["next_step"])
            self.assertIn("pptx", payload["delivery_note"]["formal_artifacts"])


if __name__ == "__main__":
    unittest.main()
