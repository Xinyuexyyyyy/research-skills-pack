import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layer2_overview_report import RelatedLink, SupervisorRow, choose_primary_list, conflict_reason


def make_row(
    name: str,
    institute: str,
    score: int,
    recommendation: str = "强烈推荐",
    fame: str = "低",
    risk: str = "低",
    freshness: str = "高",
    office_cluster_key: str = "",
    office_cluster_label: str = "",
    related_links=None,
) -> SupervisorRow:
    return SupervisorRow(
        name=name,
        research_institute=institute,
        direction_summary="测试方向",
        recent_focus="测试关注",
        field_assessment="测试评估",
        recommendation=recommendation,
        recommendation_reason="测试推荐原因",
        portrait="测试画像",
        completeness="高",
        freshness=freshness,
        freshness_note="已识别到 2025 年论文/活动信号。",
        special_note="",
        related_links=related_links or [],
        profile_path=f"{name}.md",
        office_address="测试地址",
        office_cluster_key=office_cluster_key,
        office_cluster_label=office_cluster_label,
        fame_level=fame,
        risk_level=risk,
        fit_for_apply="优先主投",
        final_score=score,
        risk_reason="公开信号相对稳定。",
        fame_reason="公开信号看更像稳健型或中生代导师，进入门槛相对友好。",
    )


class Layer2OverviewReportTests(unittest.TestCase):
    def test_strong_collaboration_blocks_same_cluster(self) -> None:
        alpha = make_row(
            "甲",
            "智能车辆研究所",
            7,
            related_links=[RelatedLink(name="乙", reason="近期论文/主页中多次共同出现", strength=3)],
        )
        beta = make_row("乙", "智能车辆研究所", 6)

        self.assertIn("同主投簇", conflict_reason(beta, alpha))

    def test_same_office_cluster_blocks_when_no_coauthor_signal(self) -> None:
        alpha = make_row("甲", "电动车辆工程技术中心", 7, office_cluster_key="车辆实验楼:41", office_cluster_label="车辆实验楼41段")
        beta = make_row("乙", "电动车辆工程技术中心", 6, office_cluster_key="车辆实验楼:41", office_cluster_label="车辆实验楼41段")

        self.assertIn("同办公簇", conflict_reason(beta, alpha))

    def test_same_institute_keeps_at_most_two_independent_clusters(self) -> None:
        rows = [
            make_row("甲", "特种车辆研究所", 7, office_cluster_key="9号楼:41", office_cluster_label="9号楼41段"),
            make_row("乙", "特种车辆研究所", 6, office_cluster_key="9号楼:43", office_cluster_label="9号楼43段"),
            make_row("丙", "特种车辆研究所", 5, office_cluster_key="9号楼:31", office_cluster_label="9号楼31段"),
        ]

        chosen, blocked = choose_primary_list(rows, max_per_institute=2)

        self.assertEqual([row.name for row in chosen], ["甲", "乙"])
        self.assertIn("主投名额已达上限", blocked["丙"])


if __name__ == "__main__":
    unittest.main()
