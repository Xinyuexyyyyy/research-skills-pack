import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layer3_overview_report import attach_scores, parse_row


SAMPLE_MD = """# 测试老师 — Layer 3 深度画像

## 基本信息

| 项目 | 内容 |
|------|------|
| 姓名 | 测试老师 |
| 研究所 | 智能车辆研究所 |
| 学院/专业 | 机械与车辆学院 |
| 职称等级 | 正高级职称 |
| 主页链接 | https://example.com |

## 最终判断

- **是否建议进入实际套磁准备**: 可以优先推进
- **主要理由**: 近两年公开论文信号连续，具备继续进入套磁准备的价值。
- **下一步动作**: 进入具体读文阶段。

## 近期主题与演化

- **主页写法**: 智能车辆;自动驾驶
- **近两年实际信号**: 智能车辆 / 自动驾驶

## 近 2 年论文

- `2024` 论文A | 主页代表作/近年成果 | 引用 0 | 作者: 作者待补充
- `2024` 论文B | 主页代表作/近年成果 | 引用 0 | 作者: 作者待补充

## 近期合作者

- **张三**: 近两年共同出现 1 次
- **李四**: 近两年共同出现 1 次

## 主页与项目动态

- **主页活跃度**: 一般
- **活跃度说明**: 主页最近可见更新约到 2024 年。

## 学生友好度观察

- **证据等级**: 中等偏强。公开来源里不只看到方向和论文，还能看到部分培养记录或组内支持条件。

## 社交平台弱信号

- **总体判断**: 平台上有院系层面的导师讨论，但没有稳定点名到这位老师，只能当外围语境。
- **小红书/知乎直接点名样本数**: 1（正向 0 / 需复核负向 0）
- **院系层面导师讨论**: 2 条；学校泛帖已剔除 1 条
"""


class Layer3OverviewReportTests(unittest.TestCase):
    def test_parse_row_extracts_key_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "测试老师_deep.md"
            path.write_text(SAMPLE_MD, encoding="utf-8")
            row = parse_row(path)

        self.assertEqual(row.name, "测试老师")
        self.assertEqual(row.research_institute, "智能车辆研究所")
        self.assertEqual(row.paper_count, 2)
        self.assertEqual(row.collaborator_count, 2)
        self.assertEqual(row.student_evidence_level, "中等偏强")
        self.assertEqual(row.direct_hits, 1)
        self.assertEqual(row.contextual_hits, 2)

    def test_attach_scores_assigns_first_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "测试老师_deep.md"
            path.write_text(SAMPLE_MD, encoding="utf-8")
            row = parse_row(path)
            ranked = attach_scores([row])

        self.assertEqual(ranked[0].read_batch, "第二批")
        self.assertGreaterEqual(ranked[0].read_priority_score, 10)


if __name__ == "__main__":
    unittest.main()
