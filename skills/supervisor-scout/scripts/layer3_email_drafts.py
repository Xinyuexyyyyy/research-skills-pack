#!/usr/bin/env python3
"""
Supervisor Scout — Layer 3 套磁邮件草案
======================================
基于论文了解文件，批量生成每位老师的套磁草案和总表。
"""

import argparse
import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)


@dataclass
class DraftRow:
    name: str
    batch: str
    judgement: str
    evidence_label: str
    recent_focus: str
    teacher_summary: str
    implication: str
    top_papers: str
    email_line: str
    next_gap: str
    file_path: str


def read_csv(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_line(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else default


def parse_understanding_file(path: Path, batch_map: Dict[str, Dict]) -> DraftRow:
    text = read_text(path)
    name = extract_line(r"# (.+?) — 论文了解文件", text)
    batch_row = batch_map.get(name, {})
    return DraftRow(
        name=name,
        batch=batch_row.get("read_batch", ""),
        judgement=batch_row.get("judgement", ""),
        evidence_label=batch_row.get("evidence_label", ""),
        recent_focus=batch_row.get("recent_focus", ""),
        teacher_summary=extract_line(r"- \*\*最近在做什么\*\*: ([^\n]+)", text),
        implication=extract_line(r"- \*\*对套磁最有用的判断\*\*: ([^\n]+)", text),
        top_papers=extract_line(r"- \*\*最稳引用论文\*\*: ([^\n]+)", text),
        email_line=extract_line(r"- \*\*这篇对邮件最有用的地方\*\*: ([^\n]+)", text),
        next_gap=extract_line(r"- \*\*还没补上的硬信息\*\*: ([^\n]+)", text),
        file_path=str(path),
    )


def send_recommendation(row: DraftRow) -> str:
    if row.evidence_label == "近年 SCI/IEEE" and row.batch == "第一批":
        return "现在就发"
    if row.evidence_label in {"近年 SCI/IEEE", "近年 DOI 期刊/会议"} and row.batch in {"第一批", "第二批"}:
        return "补一处后发"
    return "先别发"


def send_reason(row: DraftRow) -> str:
    if send_recommendation(row) == "现在就发":
        return "近两年有足够硬的论文支撑邮件主线。"
    if send_recommendation(row) == "补一处后发":
        return "论文切口已经有了，但还差一处核验或补读。"
    return "当前论文证据偏弱，先不要只靠题目级信息发信。"


def subject_line(row: DraftRow) -> str:
    focus = row.recent_focus.split("、")[0]
    return f"申请加入课题组｜{focus}方向研究兴趣"


def body_text(row: DraftRow) -> str:
    paper_refs = row.top_papers.replace("；", " 和 ")
    return (
        f"{row.name}老师，您好。\n\n"
        f"我近期系统看了您近两年的公开论文，尤其关注了 {paper_refs}。读完之后，我对您在 {row.recent_focus} 上的近期工作有了比较清楚的认识，"
        f"也觉得这条研究主线和我希望继续深入的方向比较契合。\n\n"
        f"我的理解是：{row.teacher_summary}\n"
        f"对我最有启发的一点是：{row.implication}\n\n"
        f"如果有机会进入您的课题组，我希望从 {row.email_line} 这条切口继续往下做，"
        "把问题定义、方法建模和验证闭环真正做实。"
        "如果您近期仍有招生安排，也希望有机会进一步请教您对后续研究切入点的建议。\n\n"
        "下面附上我的基本背景与简历，若您愿意进一步交流，我会非常珍惜这个机会。\n\n"
        "此致\n敬礼"
    )


def write_one_draft(row: DraftRow, output_dir: Path) -> str:
    target = output_dir / f"{row.name}_email_draft.md"
    lines = [
        f"# {row.name} — 套磁邮件草案",
        "",
        f"- **建议**: {send_recommendation(row)}",
        f"- **原因**: {send_reason(row)}",
        f"- **主线**: {row.recent_focus}",
        f"- **最该引用的论文**: {row.top_papers}",
        f"- **发前还差什么**: {row.next_gap}",
        "",
        "## 邮件标题",
        "",
        subject_line(row),
        "",
        "## 邮件正文",
        "",
        "```text",
        body_text(row),
        "```",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return str(target)


def write_master(rows: List[DraftRow], output_dir: Path) -> None:
    md_lines = [
        "# BIT 车辆 A档 套磁发信总表",
        "",
        "## 直接结论",
        "",
        f"先发：{'、'.join(row.name for row in rows if send_recommendation(row) == '现在就发') or '暂无'}。",
        f"补一处后发：{'、'.join(row.name for row in rows if send_recommendation(row) == '补一处后发') or '暂无'}。",
        f"先别发：{'、'.join(row.name for row in rows if send_recommendation(row) == '先别发') or '暂无'}。",
        "",
        "| 姓名 | 现在发吗 | 原因 | 邮件主线 | 还缺什么 | 草案 |",
        "|------|----------|------|----------|----------|------|",
    ]
    for row in rows:
        draft = output_dir / f"{row.name}_email_draft.md"
        md_lines.append(
            f"| {row.name} | {send_recommendation(row)} | {send_reason(row)} | {row.recent_focus} | {row.next_gap} | "
            f"[{draft.name}]({draft.resolve()}) |"
        )
    (output_dir / "EMAIL_MASTER.md").write_text("\n".join(md_lines), encoding="utf-8")

    with (output_dir / "EMAIL_MASTER.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "send_now", "reason", "mainline", "next_gap", "draft_path"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "name": row.name,
                "send_now": send_recommendation(row),
                "reason": send_reason(row),
                "mainline": row.recent_focus,
                "next_gap": row.next_gap,
                "draft_path": str(output_dir / f"{row.name}_email_draft.md"),
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 3 套磁邮件草案")
    parser.add_argument("--understanding-dir", required=True, help="论文了解文件目录")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--master-csv", help="LAYER3_UNDERSTANDING_MASTER.csv 路径")
    args = parser.parse_args()

    understanding_dir = Path(args.understanding_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    master_csv = Path(args.master_csv) if args.master_csv else understanding_dir / "LAYER3_UNDERSTANDING_MASTER.csv"
    batch_map = {row["name"]: row for row in read_csv(master_csv)}

    rows = []
    for path in sorted(understanding_dir.glob("*_understanding.md")):
        rows.append(parse_understanding_file(path, batch_map))

    order = {"现在就发": 0, "补一处后发": 1, "先别发": 2}
    rows.sort(key=lambda row: (order[send_recommendation(row)], row.name))

    for row in rows:
        draft_path = write_one_draft(row, output_dir)
        print(f"[保存] {row.name} -> {draft_path}")

    write_master(rows, output_dir)
    print(f"[完成] 已生成 {len(rows)} 位老师的邮件草案")


if __name__ == "__main__":
    main()
