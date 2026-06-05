#!/usr/bin/env python3
"""
Supervisor Scout — Layer 3 横向总览
===================================
从 Layer 3 深度画像目录中抽取 7 位主推荐导师的关键信息，
生成套磁前的横向总览与读文优先序。
"""

import argparse
import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)


@dataclass
class Layer3Row:
    name: str
    research_institute: str
    title_rank: str
    judgement: str
    reason: str
    next_action: str
    homepage_directions: str
    recent_focus: str
    paper_count: int
    top_papers: List[str]
    collaborator_count: int
    collaborators: List[str]
    homepage_activity: str
    homepage_activity_note: str
    student_evidence_level: str
    student_evidence_summary: str
    direct_hits: int
    positive_hits: int
    negative_hits: int
    contextual_hits: int
    filtered_generic_hits: int
    social_summary: str
    profile_path: str
    read_priority_score: int = 0
    read_batch: str = ""
    read_priority_note: str = ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_line(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else default


def extract_block(title: str, text: str) -> str:
    match = re.search(rf"## {re.escape(title)}\s+(.*?)(?=\n## |\Z)", text, re.S)
    return match.group(1).strip() if match else ""


def parse_section_bullets(title: str, text: str) -> List[str]:
    block = extract_block(title, text)
    bullets = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def parse_basic_value(label: str, text: str, default: str = "") -> str:
    pattern = rf"\| {re.escape(label)} \| (.+?) \|"
    return extract_line(pattern, text, default)


def parse_student_evidence(line: str) -> Tuple[str, str]:
    match = re.search(r"- \*\*证据等级\*\*: ([^。]+)。?(.*)", line)
    if not match:
        return "", ""
    return match.group(1).strip(), match.group(2).strip()


def parse_paper_titles(text: str) -> List[str]:
    titles = []
    for bullet in parse_section_bullets("近 2 年论文", text):
        if "近两年论文未稳定抓全" in bullet:
            continue
        bullet = re.sub(r"^`[^`]+`\s*", "", bullet)
        title = bullet.split(" | ", 1)[0].strip()
        if title:
            titles.append(title)
    return titles


def parse_collaborators(text: str) -> List[str]:
    names = []
    for bullet in parse_section_bullets("近期合作者", text):
        if "暂未从结构化论文源中稳定提取" in bullet:
            continue
        match = re.search(r"\*\*(.+?)\*\*", bullet)
        if match:
            names.append(match.group(1).strip())
    return names


def parse_row(path: Path) -> Layer3Row:
    text = read_text(path)
    name = extract_line(r"# (.+?) — Layer 3 深度画像", text)
    research_institute = parse_basic_value("研究所", text)
    title_rank = parse_basic_value("职称等级", text)
    judgement = extract_line(r"- \*\*是否建议进入实际套磁准备\*\*: ([^\n]+)", text)
    reason = extract_line(r"- \*\*主要理由\*\*: ([^\n]+)", text)
    next_action = extract_line(r"- \*\*下一步动作\*\*: ([^\n]+)", text)
    homepage_directions = extract_line(r"- \*\*主页写法\*\*: ([^\n]+)", text)
    recent_focus = extract_line(r"- \*\*近两年实际信号\*\*: ([^\n]+)", text)
    paper_titles = parse_paper_titles(text)
    collaborators = parse_collaborators(text)
    homepage_activity = extract_line(r"- \*\*主页活跃度\*\*: ([^\n]+)", text)
    homepage_activity_note = extract_line(r"- \*\*活跃度说明\*\*: ([^\n]+)", text)
    student_evidence_line = extract_line(r"(- \*\*证据等级\*\*: [^\n]+)", text)
    student_evidence_level, student_evidence_summary = parse_student_evidence(student_evidence_line)
    direct_match = re.search(
        r"- \*\*小红书/知乎直接点名样本数\*\*: (\d+)（正向 (\d+) / 需复核负向 (\d+)）",
        text,
    )
    contextual_match = re.search(r"- \*\*院系层面导师讨论\*\*: (\d+) 条；学校泛帖已剔除 (\d+) 条", text)
    social_summary = extract_line(r"- \*\*总体判断\*\*: ([^\n]+)", text)

    return Layer3Row(
        name=name,
        research_institute=research_institute,
        title_rank=title_rank,
        judgement=judgement,
        reason=reason,
        next_action=next_action,
        homepage_directions=homepage_directions,
        recent_focus=recent_focus,
        paper_count=len(paper_titles),
        top_papers=paper_titles[:3],
        collaborator_count=len(collaborators),
        collaborators=collaborators[:5],
        homepage_activity=homepage_activity,
        homepage_activity_note=homepage_activity_note,
        student_evidence_level=student_evidence_level,
        student_evidence_summary=student_evidence_summary,
        direct_hits=int(direct_match.group(1)) if direct_match else 0,
        positive_hits=int(direct_match.group(2)) if direct_match else 0,
        negative_hits=int(direct_match.group(3)) if direct_match else 0,
        contextual_hits=int(contextual_match.group(1)) if contextual_match else 0,
        filtered_generic_hits=int(contextual_match.group(2)) if contextual_match else 0,
        social_summary=social_summary,
        profile_path=str(path),
    )


def score_row(row: Layer3Row) -> Tuple[int, str, str]:
    score = 0
    if row.judgement == "可以优先推进":
        score += 5
    elif row.judgement == "可推进但需补核验":
        score += 3
    else:
        score += 1

    score += {"中等偏强": 3, "中等": 2, "偏弱": 0}.get(row.student_evidence_level, 1)
    score += 2 if row.paper_count >= 4 else 1 if row.paper_count >= 2 else 0
    score += {"较活跃": 2, "一般": 1, "偏旧": 0, "未知": 0}.get(row.homepage_activity, 0)
    score += 1 if row.direct_hits > 0 else 0
    score -= 1 if row.negative_hits > 0 else 0

    if row.judgement == "可以优先推进" and row.paper_count >= 3:
        batch = "第一批"
        note = "适合优先进入逐篇读文和邮件切入点设计。"
    elif row.paper_count >= 2 or row.student_evidence_level == "中等偏强":
        batch = "第二批"
        note = "公开信号已够支撑读文，但发信前仍要补一个关键核验点。"
    else:
        batch = "第三批"
        note = "建议先做补核验式读文，避免直接按主页印象写套磁。"
    return score, batch, note


def attach_scores(rows: List[Layer3Row]) -> List[Layer3Row]:
    for row in rows:
        row.read_priority_score, row.read_batch, row.read_priority_note = score_row(row)
    rows.sort(
        key=lambda item: (
            item.read_priority_score,
            item.paper_count,
            item.direct_hits,
            item.collaborator_count,
            item.name,
        ),
        reverse=True,
    )
    return rows


def build_global_summary(rows: List[Layer3Row]) -> List[str]:
    ready = [row.name for row in rows if row.judgement == "可以优先推进"]
    second = [row.name for row in rows if row.read_batch == "第二批"]
    third = [row.name for row in rows if row.read_batch == "第三批"]
    direct_social = [row.name for row in rows if row.direct_hits > 0]
    old_homepage = [row.name for row in rows if row.homepage_activity == "偏旧"]

    lines = [
        "## 总调研摘要",
        "",
        f"当前 7 位主推荐导师里，已经可以直接进入读文准备的第一批对象是：{'、'.join(ready) if ready else '暂无'}。",
        f"第二批适合紧跟推进的是：{'、'.join(second) if second else '暂无'}；第三批则是：{'、'.join(third) if third else '暂无'}。",
        "",
        "这一版 Layer 3 总览不再看谁“名气大”，而是优先看三个更实际的套磁前信号：",
        "- 近 2 年论文是否连续，能不能撑起读文切入口。",
        "- 学生友好度证据是否不只停留在主页标签，而是能看到培养记录、资源支持、公开招收态度。",
        "- 主页是否偏旧，是否需要在读文阶段顺手补核最近学生/合作者线索。",
        "",
        f"从当前公开信号看，{('、'.join(direct_social) + ' ') if direct_social else ''}在社交平台上至少能检到少量直接点名线索，但这些仍然只能算弱信号，不能直接当事实。"
        if direct_social else
        "当前大多数老师仍然缺少直接点名的公开学生讨论，所以读文版阶段要把“近期作者梯队”和“实际招生状态”当成更硬的判断依据。",
        f"{'、'.join(old_homepage)} 的主页整体偏旧，后续写套磁时要更依赖近两年论文和作者结构，而不是依赖主页措辞。"
        if old_homepage else
        "这批老师的主页时效整体还可以，读文版可以直接把主页描述当辅助背景。",
    ]
    return lines


def build_priority_section(rows: List[Layer3Row]) -> List[str]:
    lines = [
        "## 建议读文顺序",
        "",
        "| 顺序 | 姓名 | 研究所 | 批次 | 当前判断 | 证据等级 | 近2年论文数 | 主页活跃度 | 为什么先读 |",
        "|------|------|--------|------|----------|----------|-------------|------------|------------|",
    ]
    for idx, row in enumerate(rows, start=1):
        why = row.read_priority_note.replace("。", "")
        lines.append(
            f"| {idx} | {row.name} | {row.research_institute} | {row.read_batch} | {row.judgement} | "
            f"{row.student_evidence_level or '待补'} | {row.paper_count} | {row.homepage_activity} | {why} |"
        )
    return lines


def build_focus_section(rows: List[Layer3Row]) -> List[str]:
    lines = [
        "## 七人横向总览",
        "",
        "| 姓名 | 研究所 | 近期主题 | 近2年论文数 | 合作者线索 | 学生友好度 | 社交弱信号 | 当前卡点 |",
        "|------|--------|----------|-------------|------------|------------|------------|----------|",
    ]
    for row in rows:
        collab = f"{row.collaborator_count}人" if row.collaborator_count else "暂无稳定结构化线索"
        social = f"直点 {row.direct_hits} / 院系 {row.contextual_hits}"
        lines.append(
            f"| {row.name} | {row.research_institute} | {row.recent_focus} | {row.paper_count} | "
            f"{collab} | {row.student_evidence_level or '待补'} | {social} | {row.next_action} |"
        )
    return lines


def build_reading_brief(rows: List[Layer3Row]) -> List[str]:
    lines = ["## 单人读文提示", ""]
    for row in rows:
        top_titles = "；".join(row.top_papers[:2]) if row.top_papers else "近两年论文仍需人工补抓"
        collab = "、".join(row.collaborators[:3]) if row.collaborators else "暂无稳定结构化合作者"
        lines.extend([
            f"### {row.name}",
            f"- **当前定位**: {row.judgement}；{row.student_evidence_level or '证据待补'}。",
            f"- **建议先读**: {top_titles}",
            f"- **读文时重点看**: {row.recent_focus}",
            f"- **顺手核验**: {collab}；{row.homepage_activity_note}",
            f"- **画像原文**: [{Path(row.profile_path).name}]({Path(row.profile_path).resolve()})",
            "",
        ])
    return lines


def build_group_notes(rows: List[Layer3Row]) -> List[str]:
    by_group: Dict[str, List[str]] = {}
    for row in rows:
        by_group.setdefault(row.research_institute, []).append(row.name)

    lines = ["## 同所提醒", ""]
    for institute, names in by_group.items():
        if len(names) == 1:
            lines.append(f"- `{institute}`: 当前只有 {names[0]} 进入 Layer 3 主推荐，可直接按单目标推进。")
        else:
            lines.append(
                f"- `{institute}`: 当前 Layer 3 名单里有 {'、'.join(names)}。读文可以并行，但真正发信前仍要回到去重原则，避免同组/同合作簇重复主投。"
            )
    return lines


def write_csv(rows: List[Layer3Row], path: Path) -> None:
    fieldnames = [
        "name",
        "research_institute",
        "title_rank",
        "judgement",
        "recent_focus",
        "paper_count",
        "collaborator_count",
        "homepage_activity",
        "student_evidence_level",
        "direct_hits",
        "contextual_hits",
        "filtered_generic_hits",
        "read_priority_score",
        "read_batch",
        "read_priority_note",
        "next_action",
        "profile_path",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "name": row.name,
                "research_institute": row.research_institute,
                "title_rank": row.title_rank,
                "judgement": row.judgement,
                "recent_focus": row.recent_focus,
                "paper_count": row.paper_count,
                "collaborator_count": row.collaborator_count,
                "homepage_activity": row.homepage_activity,
                "student_evidence_level": row.student_evidence_level,
                "direct_hits": row.direct_hits,
                "contextual_hits": row.contextual_hits,
                "filtered_generic_hits": row.filtered_generic_hits,
                "read_priority_score": row.read_priority_score,
                "read_batch": row.read_batch,
                "read_priority_note": row.read_priority_note,
                "next_action": row.next_action,
                "profile_path": row.profile_path,
            })


def write_markdown(rows: List[Layer3Row], path: Path) -> None:
    lines = [
        "# BIT 车辆 A档 Layer 3 横向总览",
        "",
        *build_global_summary(rows),
        "",
        *build_priority_section(rows),
        "",
        *build_focus_section(rows),
        "",
        *build_group_notes(rows),
        "",
        *build_reading_brief(rows),
        "## 说明",
        "",
        "- 这份文档的作用是给 `Layer 3` 一个全局视图，并给出进入“套磁前读文版”的顺序建议。",
        "- 社交平台命中仍然只是弱信号，真正写邮件前还是要回到近两年论文、作者结构和实际招生状态。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 3 横向总览")
    parser.add_argument("--profiles-dir", required=True, help="Layer 3 深度画像目录")
    parser.add_argument("--output-md", help="输出 Markdown 路径")
    parser.add_argument("--output-csv", help="输出 CSV 路径")
    args = parser.parse_args()

    profiles_dir = Path(args.profiles_dir)
    profile_files = sorted(profiles_dir.glob("*_deep.md"))
    if not profile_files:
        raise SystemExit("未找到 Layer 3 深度画像文件。")

    rows = attach_scores([parse_row(path) for path in profile_files])
    output_md = Path(args.output_md) if args.output_md else profiles_dir / "LAYER3_OVERVIEW.md"
    output_csv = Path(args.output_csv) if args.output_csv else profiles_dir / "LAYER3_OVERVIEW.csv"
    write_markdown(rows, output_md)
    write_csv(rows, output_csv)
    print(f"[完成] 已生成 {output_md}")
    print(f"[完成] 已生成 {output_csv}")


if __name__ == "__main__":
    main()
