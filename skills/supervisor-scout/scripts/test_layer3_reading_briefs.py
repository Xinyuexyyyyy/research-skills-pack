import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layer3_reading_briefs import clean_title_candidate, extract_doi, parse_paper_entries, venue_tier, PaperEntry, PaperMetadata


SAMPLE_MD = """# 测试老师 — Layer 3 深度画像

## 近 2 年论文

- `2025` TP-FRL: An Efficient and Adaptive Trajectory Prediction Method Based on the Rule and Learning-Based Frameworks Fusion[J]. IEEE Transactions on Intelligent Vehicles, 2024, Vol.9 | 主页代表作/近年成果 | 引用 0 | 作者: 作者待补充
- `2025` Yechen Qin , Zhewei Zhu, Yunping Zhou, Guangyu Bai, Kui Wang, Tao Xu*, Bi-Level Optimization for Closed-Loop Model Reference Adaptive Vibration Control in Wheeled-Legged Multimode Vehicles, IEEE Transactions on Industrial Electronics , DOI: 10.1109/TIE.2025.3528486, 2025.(SCI, Q1, IF 7.5) | 主页代表作/近年成果 | 引用 0 | 作者: 作者待补充
"""


class Layer3ReadingBriefsTests(unittest.TestCase):
    def test_extract_doi(self) -> None:
        text = "DOI: 10.1109/TIE.2025.3528486, 2025."
        self.assertEqual(extract_doi(text), "10.1109/TIE.2025.3528486")

    def test_clean_title_candidate_prefers_title_like_segment(self) -> None:
        raw = "Yechen Qin , Zhewei Zhu, Yunping Zhou, Guangyu Bai, Kui Wang, Tao Xu*, Bi-Level Optimization for Closed-Loop Model Reference Adaptive Vibration Control in Wheeled-Legged Multimode Vehicles, IEEE Transactions on Industrial Electronics , DOI: 10.1109/TIE.2025.3528486"
        title = clean_title_candidate(raw)
        self.assertIn("Bi-Level Optimization for Closed-Loop Model Reference Adaptive Vibration Control", title)

    def test_parse_paper_entries_extracts_year_title_and_doi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "测试老师_deep.md"
            path.write_text(SAMPLE_MD, encoding="utf-8")
            entries = parse_paper_entries(path)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].year, 2025)
        self.assertTrue(entries[1].doi.startswith("10.1109/TIE"))

    def test_venue_tier_prefers_recent_ieee(self) -> None:
        entry = PaperEntry(year=2025, raw_title="X", venue="IEEE Transactions on Intelligent Vehicles", cited=0, authors=[])
        meta = PaperMetadata(
            title="X",
            doi="10.1109/TIV.2025.1",
            year=2025,
            venue="IEEE Transactions on Intelligent Vehicles",
            abstract="test",
            url="",
            authors=[],
            citation_count=0,
            source="test",
            confidence="高",
        )
        score, label = venue_tier(meta, entry)
        self.assertEqual(score, 3)
        self.assertEqual(label, "近年 SCI/IEEE")


if __name__ == "__main__":
    unittest.main()
