import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layer3_deep_profiles import (
    analyze_social_results,
    extract_recent_collaborators,
    extract_reliable_scholar_recent_papers,
    extract_structured_homepage_recent_papers,
    load_target_rows,
)


class Layer3DeepProfilesTests(unittest.TestCase):
    def test_extract_recent_collaborators_counts_unique_per_paper(self) -> None:
        papers = [
            {"authors": ["张三", "李四", "王五"]},
            {"authors": ["张三", "李四", "赵六"]},
            {"authors": ["张三", "李四", "李四", "王五"]},
        ]

        collabs = extract_recent_collaborators("张三", papers)

        self.assertEqual(collabs[0], ("李四", 3))
        self.assertEqual(collabs[1], ("王五", 2))

    def test_load_target_rows_uses_primary_bucket_from_overview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            candidates = tmpdir / "candidates.csv"
            overview = tmpdir / "overview.csv"

            with candidates.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["name", "research_institute", "profile_url"])
                writer.writeheader()
                writer.writerow({"name": "甲", "research_institute": "A所", "profile_url": "u1"})
                writer.writerow({"name": "乙", "research_institute": "B所", "profile_url": "u2"})

            with overview.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["name", "priority_bucket"])
                writer.writeheader()
                writer.writerow({"name": "乙", "priority_bucket": "备选"})
                writer.writerow({"name": "甲", "priority_bucket": "主推荐"})

            rows = load_target_rows(str(candidates), str(overview), [])
            self.assertEqual([row["name"] for row in rows], ["甲"])

    def test_analyze_social_results_distinguishes_direct_and_school_level_hits(self) -> None:
        social_data = {
            "xiaohongshu": [
                {"title": "北京理工大学张三导师避雷", "author": "a", "url": "u1"},
                {"title": "北京理工大学神仙导师汇总", "author": "b", "url": "u2"},
            ],
            "zhihu": [
                {"title": "你在北理遇到哪些值得推荐的研究生导师？", "author": "c", "url": "u3"},
            ],
            "douyin_note": "not supported",
        }

        summary = analyze_social_results("张三", ["北京理工大学", "北理"], social_data)

        self.assertEqual(summary["direct_hits"], 1)
        self.assertEqual(summary["negative_hits"], 1)
        self.assertIn("负面题名", summary["summary"])

    def test_analyze_social_results_filters_generic_school_noise(self) -> None:
        social_data = {
            "xiaohongshu": [
                {"title": "北京理工大学2024年度新增列硕士生导师名单", "author": "a", "url": "u1"},
                {"title": "北理工车辆工程有哪些值得推荐的导师？", "author": "b", "url": "u2"},
            ],
            "zhihu": [],
            "douyin_note": "not supported",
        }

        summary = analyze_social_results("张三", ["北京理工大学", "北理"], social_data)

        self.assertEqual(summary["direct_hits"], 0)
        self.assertEqual(summary["contextual_hits"], 1)
        self.assertEqual(summary["generic_school_hits"], 1)
        self.assertEqual(len(summary["entries"]), 1)

    def test_extract_structured_homepage_recent_papers_splits_long_section(self) -> None:
        section = (
            "近五年5篇论文代表作: [1] TP-FRL: An Efficient and Adaptive Trajectory Prediction Method Based on the Rule "
            "and Learning-Based Frameworks Fusion[J]. IEEE Transactions on Intelligent Vehicles, 2024, Vol.9(1): 2210-2222. "
            "[2] Hierarchical Trajectory Planning Based on Adaptive Motion Primitives and Bilevel Corridor[J]. "
            "IEEE Transactions on Vehicular Technology, 2024, Vol.73(11): 1-17. "
            "主要在研项目： [1] 国家自然科学基金面上项目，2022.1-2025.12"
        )

        papers = extract_structured_homepage_recent_papers(section)

        self.assertEqual(len(papers), 2)
        self.assertTrue(all(p["year"] == 2024 for p in papers))
        self.assertTrue(all("项目" not in p["title"] for p in papers))

    def test_extract_reliable_scholar_recent_papers_requires_target_author(self) -> None:
        row = {"name": "于会龙", "direction_keywords": "智能车辆 / 自动驾驶"}
        scholar = {
            "items": [
                {
                    "title": "基于MLP-SVM 的驾驶员换道行为预测",
                    "meta": "密俊霞， 于会龙 ， 席军强 - 兵工学报, 2024 - co-journal.com",
                    "year": 2024,
                    "cited": 5,
                },
                {
                    "title": "热液矿床成矿期与成矿阶段划分中的常见问题与关注方向",
                    "meta": "于会 冬， 任廷聪， 龙训荣 - 矿物岩石, 2025 - kwys.cdut.edu.cn",
                    "year": 2025,
                    "cited": 0,
                },
            ]
        }

        papers = extract_reliable_scholar_recent_papers(row, scholar)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["title"], "基于MLP-SVM 的驾驶员换道行为预测")

    def test_extract_reliable_scholar_recent_papers_rejects_wrong_initials(self) -> None:
        row = {"name": "于会龙", "direction_keywords": "智能车辆 / 自动驾驶"}
        scholar = {
            "items": [
                {
                    "title": "Comprehensive review on smart highway evolution and research 2025",
                    "meta": "Y LI, X HUANG, J ZHANG, S LI, G YU - Journal of highway, 2025 - sciengine.com",
                    "year": 2025,
                    "cited": 0,
                }
            ]
        }

        papers = extract_reliable_scholar_recent_papers(row, scholar)

        self.assertEqual(papers, [])


if __name__ == "__main__":
    unittest.main()
