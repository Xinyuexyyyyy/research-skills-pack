import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layer3_email_drafts import parse_understanding_file, send_recommendation


SAMPLE_UNDERSTANDING = """# 测试老师 — 论文了解文件

## 一眼结论

- **最近在做什么**: 测试老师近两年的公开工作集中在智能车辆 / 自动驾驶。
- **对套磁最有用的判断**: 联系测试老师时，邮件主线应直接落到代表论文里的具体问题和方法。
- **证据硬度**: 近年 SCI/IEEE
- **最稳引用论文**: Test Paper A
- **当前最大卡点**: 进入具体读文阶段。

## 核心论文 1

- **标题**: Test Paper A
- **来源**: 2025 / IEEE Transactions on Intelligent Vehicles
- **引用等级**: 近年 SCI/IEEE，DOI 10.1109/TIV.2025.1
- **作者**: A，B，C
- **你该抓的点**: 核心是复杂场景下的轨迹规划或预测。
- **这篇对邮件最有用的地方**: 邮件里可以从复杂场景下的规划-控制闭环切入。
- **当前风险**: 核心实验仍需回原文核对。

## 最后判断

- **现在建议**: 可以先发
- **最稳邮件主线**: 把邮件落在智能车辆 / 自动驾驶上。
- **还没补上的硬信息**: 进入具体读文阶段。
"""


class Layer3EmailDraftsTests(unittest.TestCase):
    def test_parse_understanding_file_reads_new_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "测试老师_understanding.md"
            path.write_text(SAMPLE_UNDERSTANDING, encoding="utf-8")
            row = parse_understanding_file(path, {"测试老师": {"read_batch": "第一批", "judgement": "可以优先推进", "recent_focus": "智能车辆 / 自动驾驶", "evidence_label": "近年 SCI/IEEE"}})

        self.assertEqual(row.name, "测试老师")
        self.assertEqual(row.evidence_label, "近年 SCI/IEEE")
        self.assertIn("Test Paper A", row.top_papers)
        self.assertEqual(send_recommendation(row), "现在就发")


if __name__ == "__main__":
    unittest.main()
