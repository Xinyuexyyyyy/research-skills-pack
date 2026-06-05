#!/usr/bin/env python3
"""
Supervisor Scout — Layer 2 横向总览与推荐名单
============================================
从 Layer 2 画像目录解析出总览表，并生成去重后的推荐名单。

这一版把“研究所级去重”升级为“课题组/合作簇优先去重”：
- 先看 `可能同组 / 强合作老师` 里的共同署名强信号
- 再看 `办公地址` 是否落在同一办公簇
- 允许同一研究所保留不同主投簇，但默认每所最多保留 2 位主投
"""

import argparse
import csv
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)


@dataclass
class RelatedLink:
    name: str
    reason: str
    strength: int


@dataclass
class SupervisorRow:
    name: str
    research_institute: str
    direction_summary: str
    recent_focus: str
    field_assessment: str
    recommendation: str
    recommendation_reason: str
    portrait: str
    completeness: str
    freshness: str
    freshness_note: str
    special_note: str
    related_links: List[RelatedLink]
    profile_path: str
    office_address: str
    office_cluster_key: str
    office_cluster_label: str
    fame_level: str
    risk_level: str
    fit_for_apply: str
    final_score: int
    risk_reason: str
    fame_reason: str
    primary_note: str = ""
    blocked_reason: str = ""
    priority_bucket: str = ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.S)
    return match.group(1).strip() if match else default


def extract_line(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else default


def normalize_compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def parse_related(text: str) -> List[RelatedLink]:
    match = re.search(r"## 可能同组 / 强合作老师\s+(.*?)(?:\n---|\Z)", text, re.S)
    if not match:
        return []

    links: List[RelatedLink] = []
    for line in match.group(1).splitlines():
        parsed = re.search(r"- \*\*(.+?)\*\*: (.+)", line)
        if not parsed:
            continue
        name, reason = parsed.groups()
        strength = 0
        if "多次共同出现" in reason:
            strength = 3
        elif "共同署名" in reason:
            strength = 2
        links.append(RelatedLink(name=name.strip(), reason=reason.strip(), strength=strength))
    return links


def score_recommendation(level: str) -> int:
    return {
        "强烈推荐": 4,
        "推荐": 3,
        "可作为备选": 1,
        "谨慎": -2,
    }.get(level, 0)


def score_freshness(level: str) -> int:
    return {"高": 2, "中": 1, "低": -2}.get(level, 0)


def score_completeness(level: str) -> int:
    return {"高": 1, "中": 0, "低": -1}.get(level, 0)


def infer_fame_level(name: str, portrait: str, special_note: str, recommendation_reason: str) -> Tuple[str, str]:
    joined = f"{name} {portrait} {special_note} {recommendation_reason}"
    if any(keyword in joined for keyword in ["院士", "高被引", "顶层平台型导师"]):
        return "高", "名气或平台层级很高，进组竞争和分流风险都更大。"
    if any(keyword in joined for keyword in ["平台/团队型导师", "学术影响力较强"]):
        return "中", "团队或学术影响力不小，属于有一定竞争的老师。"
    return "低", "公开信号看更像稳健型或中生代导师，进入门槛相对友好。"


def infer_risk_level(
    freshness: str,
    completeness: str,
    special_note: str,
    recommendation: str,
    freshness_note: str,
) -> Tuple[str, str]:
    reasons = []
    score = 0

    if recommendation == "谨慎":
        score += 3
        reasons.append("系统已给出谨慎评级")
    if freshness == "低":
        score += 3
        reasons.append("近年公开信号偏旧")
    elif freshness == "中":
        score += 1
        reasons.append("近年公开信号一般")

    if completeness == "低":
        score += 2
        reasons.append("信息完整度偏低")

    if any(keyword in special_note for keyword in ["调任", "退休", "副院长", "行政"]):
        score += 3
        reasons.append(special_note)
    elif special_note:
        score += 1
        reasons.append(special_note)

    if "疑似过时" in freshness_note:
        score += 1

    if score >= 5:
        return "高", "；".join(reasons) if reasons else "存在明显不确定性。"
    if score >= 2:
        return "中", "；".join(reasons) if reasons else "存在一定不确定性。"
    return "低", "公开信号相对稳定。"


def infer_fit_for_apply(fame_level: str, risk_level: str, recommendation: str) -> str:
    if risk_level == "高" or recommendation == "谨慎":
        return "不建议主投"
    if fame_level == "高":
        return "可冲但不宜主投"
    if fame_level == "中":
        return "适合认真投递"
    return "优先主投"


def infer_office_cluster(address: str) -> Tuple[str, str]:
    compact = normalize_compact(address)
    if not compact or compact == "待补充":
        return "", ""

    building = ""
    for token, label in [
        ("国防科技园5号楼", "国防科技园5号楼"),
        ("车辆重点实验楼", "车辆重点实验楼"),
        ("车辆实验楼", "车辆实验楼"),
        ("9号教学楼", "9号楼"),
        ("9号楼", "9号楼"),
        ("1号教学楼", "1号楼"),
        ("1号楼", "1号楼"),
    ]:
        if token in compact:
            building = label
            break

    if not building:
        return "", ""

    room_match = re.search(r"(\d{3})([A-Za-z])?", compact)
    if room_match:
        room = room_match.group(1)
        segment = room[:2]
        return f"{building}:{segment}", f"{building}{segment}段"

    floor_match = re.search(r"(\d)层", compact)
    if floor_match:
        floor = floor_match.group(1)
        return f"{building}:{floor}层", f"{building}{floor}层"

    return "", ""


def parse_profile(path: Path) -> SupervisorRow:
    text = read_text(path)
    name = path.stem.replace("_profile", "")
    research_institute = extract_line(r"\| \*\*研究所\*\* \| (.+?) \|", text)
    office_address = extract_line(r"\| \*\*办公地址\*\* \| (.+?) \|", text, "待补充")
    direction_summary = extract_line(r"\*\*研究方向归纳\*\*: ([^\n]+)", text)
    recent_focus = extract_line(r"\*\*最近关注\*\*: ([^\n]+)", text)
    field_assessment = extract_line(r"\*\*这个方向好不好做\*\*: ([^\n]+)", text)
    rec_match = re.search(r"\*\*是否推荐\*\*: ([^。]+)。([^\n]+)", text)
    recommendation = rec_match.group(1).strip() if rec_match else ""
    recommendation_reason = rec_match.group(2).strip() if rec_match else ""
    portrait = extract_line(r"\*\*综合科研画像\*\*: ([^\n]+)", text)
    completeness = extract_line(r"\*\*信息完整度\*\*: (高|中|低)", text)
    freshness = extract_line(r"\*\*信息新鲜度\*\*: (高|中|低)", text)
    freshness_note = extract_line(r"\*\*新鲜度说明\*\*: ([^\n]+)", text)
    special_note = extract(r"## 特殊注意点\s+- (.+?)(?:\n##|\n---|\Z)", text)
    related_links = parse_related(text)

    fame_level, fame_reason = infer_fame_level(name, portrait, special_note, recommendation_reason)
    risk_level, risk_reason = infer_risk_level(freshness, completeness, special_note, recommendation, freshness_note)
    fit_for_apply = infer_fit_for_apply(fame_level, risk_level, recommendation)
    final_score = score_recommendation(recommendation) + score_freshness(freshness) + score_completeness(completeness)
    final_score -= {"高": 3, "中": 1, "低": 0}[fame_level]
    final_score -= {"高": 3, "中": 1, "低": 0}[risk_level]
    office_cluster_key, office_cluster_label = infer_office_cluster(office_address)

    return SupervisorRow(
        name=name,
        research_institute=research_institute,
        direction_summary=direction_summary,
        recent_focus=recent_focus,
        field_assessment=field_assessment,
        recommendation=recommendation,
        recommendation_reason=recommendation_reason,
        portrait=portrait,
        completeness=completeness,
        freshness=freshness,
        freshness_note=freshness_note,
        special_note=special_note,
        related_links=related_links,
        profile_path=str(path),
        office_address=office_address,
        office_cluster_key=office_cluster_key,
        office_cluster_label=office_cluster_label,
        fame_level=fame_level,
        risk_level=risk_level,
        fit_for_apply=fit_for_apply,
        final_score=final_score,
        risk_reason=risk_reason,
        fame_reason=fame_reason,
    )


def direct_link_strength(left: SupervisorRow, right: SupervisorRow) -> int:
    strength = 0
    for link in left.related_links:
        if link.name == right.name:
            strength = max(strength, link.strength)
    for link in right.related_links:
        if link.name == left.name:
            strength = max(strength, link.strength)
    return strength


def conflict_reason(left: SupervisorRow, right: SupervisorRow) -> str:
    if left.research_institute != right.research_institute:
        return ""

    strength = direct_link_strength(left, right)
    if strength >= 3:
        return f"与已选 {right.name} 存在多次共同出现信号，判为同主投簇。"
    if strength >= 2:
        return f"与已选 {right.name} 存在共同署名信号，判为同主投簇。"

    if left.office_cluster_key and left.office_cluster_key == right.office_cluster_key:
        cluster_label = left.office_cluster_label or right.office_cluster_label or "同办公簇"
        return f"与已选 {right.name} 落在同办公簇（{cluster_label}），不再重复主投。"

    return ""


def build_primary_note(row: SupervisorRow, existing_same_institute: List[SupervisorRow]) -> str:
    if not existing_same_institute:
        if row.office_cluster_label:
            return f"作为该所当前优先入口，办公簇定位在 {row.office_cluster_label}。"
        return "作为该所当前优先入口，未发现需要先避开的同簇主投对象。"

    peer_names = "、".join(peer.name for peer in existing_same_institute)
    if row.office_cluster_label:
        return f"与 {peer_names} 无直接强合作或同办公簇冲突，可视作 {row.office_cluster_label} 的独立主投簇。"
    return f"与 {peer_names} 无直接强合作或同办公簇冲突，可视作独立主投簇。"


def choose_primary_list(rows: List[SupervisorRow], max_per_institute: int) -> Tuple[List[SupervisorRow], Dict[str, str]]:
    candidates = [
        row for row in rows
        if row.recommendation in {"强烈推荐", "推荐"} and row.risk_level != "高" and row.fame_level != "高"
    ]
    candidates.sort(
        key=lambda row: (
            row.final_score,
            row.fame_level == "低",
            row.recommendation == "强烈推荐",
            row.freshness == "高",
        ),
        reverse=True,
    )

    chosen: List[SupervisorRow] = []
    blocked: Dict[str, str] = {}
    institute_counts: Dict[str, int] = defaultdict(int)

    for row in candidates:
        same_institute_chosen = [item for item in chosen if item.research_institute == row.research_institute]
        if institute_counts[row.research_institute] >= max_per_institute:
            blocked[row.name] = f"{row.research_institute} 主投名额已达上限（{max_per_institute}）。"
            continue

        reason = ""
        for selected in same_institute_chosen:
            reason = conflict_reason(row, selected)
            if reason:
                break
        if reason:
            blocked[row.name] = reason
            continue

        row.primary_note = build_primary_note(row, same_institute_chosen)
        row.priority_bucket = "主推荐"
        chosen.append(row)
        institute_counts[row.research_institute] += 1

    return chosen, blocked


def choose_backup_list(rows: List[SupervisorRow], chosen: List[SupervisorRow], blocked: Dict[str, str]) -> List[SupervisorRow]:
    chosen_names = {row.name for row in chosen}
    backups = [
        row for row in rows
        if row.name not in chosen_names and row.recommendation in {"强烈推荐", "推荐"} and row.risk_level != "高"
    ]
    for row in backups:
        row.blocked_reason = blocked.get(row.name, "")
        row.priority_bucket = "备选"

    backups.sort(
        key=lambda row: (
            row.final_score,
            row.fame_level == "低",
            bool(row.blocked_reason),
        ),
        reverse=True,
    )
    return backups[:10]


def assign_priority_buckets(rows: List[SupervisorRow], chosen: List[SupervisorRow], backups: List[SupervisorRow]) -> None:
    chosen_names = {row.name for row in chosen}
    backup_names = {row.name for row in backups}
    for row in rows:
        if row.name in chosen_names:
            row.priority_bucket = "主推荐"
        elif row.name in backup_names:
            row.priority_bucket = "备选"
        elif row.risk_level == "高" or row.fame_level == "高":
            row.priority_bucket = "主动降权"
        else:
            row.priority_bucket = "全量"


def write_csv(rows: List[SupervisorRow], path: Path) -> None:
    fields = [
        "name", "research_institute", "office_address", "office_cluster_label",
        "direction_summary", "recent_focus", "recommendation", "recommendation_reason",
        "completeness", "freshness", "fame_level", "fame_reason",
        "risk_level", "risk_reason", "fit_for_apply", "final_score",
        "priority_bucket", "primary_note", "blocked_reason",
        "special_note", "related_detail", "profile_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "name": row.name,
                "research_institute": row.research_institute,
                "office_address": row.office_address,
                "office_cluster_label": row.office_cluster_label,
                "direction_summary": row.direction_summary,
                "recent_focus": row.recent_focus,
                "recommendation": row.recommendation,
                "recommendation_reason": row.recommendation_reason,
                "completeness": row.completeness,
                "freshness": row.freshness,
                "fame_level": row.fame_level,
                "fame_reason": row.fame_reason,
                "risk_level": row.risk_level,
                "risk_reason": row.risk_reason,
                "fit_for_apply": row.fit_for_apply,
                "final_score": row.final_score,
                "priority_bucket": row.priority_bucket,
                "primary_note": row.primary_note,
                "blocked_reason": row.blocked_reason,
                "special_note": row.special_note,
                "related_detail": " / ".join(f"{link.name}:{link.reason}" for link in row.related_links),
                "profile_path": row.profile_path,
            })


def build_markdown(rows: List[SupervisorRow], chosen: List[SupervisorRow], backups: List[SupervisorRow], max_per_institute: int) -> str:
    deprioritized = [
        row for row in rows
        if row.fame_level == "高" or row.risk_level == "高"
    ]
    chosen_names = "、".join(row.name for row in chosen)
    lines = [
        "# BIT 车辆 A档 Layer 2 横向总览",
        "",
        "## 总调研摘要",
        "",
        f"这轮 Layer 2 调整后，主推荐名单收敛为：{chosen_names}。",
        "",
        "整体策略已经从“研究所级去重”升级为“真实主投簇优先去重”：优先避开有明显共同署名、近期多次共同出现、或办公位置高度接近的老师组合，避免把看起来属于同一课题组/同一合作簇的人同时放进主投名单。",
        "",
        "从当前公开信号看，电动车辆工程技术中心和智能车辆研究所内部都还能拆出不止一个主投入口，但不适合无上限扩张，所以这版默认控制为“同所最多 2 位主投”。特种车辆研究所内部强合作更密，最终保留为李雪原、闫清东两个相对独立的入口；振动与声学研究所则只保留秦也辰，避免与董明明重复主投。",
        "",
        "这份名单仍然只是 Layer 2 的投递优先级建议，不是最终套磁清单。真正发信前，主推荐对象仍然需要进入 Layer 3，重点核验最近 2 年论文、稳定合作者、实际招生状态，以及是否存在比当前公开信息更真实的组内从属关系。",
        "",
        "## 筛选规则",
        "",
        "- 主推荐名单优先保留 `强烈推荐/推荐`、`风险度不高`、`名气不过大` 的老师。",
        "- 去重逻辑先看 `共同署名/多次共同出现`，再看 `办公地址办公簇`，不再只按研究所一刀切。",
        f"- 同一研究所允许保留不同主投簇，但默认每所最多保留 `{max_per_institute}` 位主投，避免投递过密。",
        "- `名气太大` 的判断依据：院士、高被引、顶层平台型导师，或明显的大团队/强平台负责人。",
        "- `风险度` 主要综合新鲜度、特殊状态（调任/退休/行政）和信息完整度。",
        "",
        "## 主推荐名单",
        "",
        "| 姓名 | 研究所 | 方向 | 推荐原因 | 去重依据 | 投递建议 |",
        "|------|--------|------|----------|----------|----------|",
    ]

    for row in chosen:
        lines.append(
            f"| {row.name} | {row.research_institute} | {row.direction_summary} | "
            f"{row.recommendation_reason} | {row.primary_note} | {row.fit_for_apply} |"
        )

    lines.extend([
        "",
        "## 本轮去重观察",
        "",
    ])
    for institute in ["电动车辆工程技术中心", "智能车辆研究所", "特种车辆研究所", "振动与声学研究所"]:
        selected = [row for row in chosen if row.research_institute == institute]
        if not selected:
            continue
        summary = "；".join(f"{row.name}：{row.primary_note}" for row in selected)
        lines.append(f"- `{institute}`: {summary}")

    lines.extend([
        "",
        "## 备选名单",
        "",
        "| 姓名 | 研究所 | 推荐度 | 名气 | 风险度 | 未进主推的主要原因 |",
        "|------|--------|--------|------|--------|--------------------|",
    ])
    for row in backups:
        note = row.blocked_reason or row.special_note or row.fame_reason
        lines.append(
            f"| {row.name} | {row.research_institute} | {row.recommendation} | "
            f"{row.fame_level} | {row.risk_level} | {note} |"
        )

    lines.extend([
        "",
        "## 主动降权 / 不建议主投对象",
        "",
        "| 姓名 | 研究所 | 原因 |",
        "|------|--------|------|",
    ])
    for row in sorted(deprioritized, key=lambda item: (item.risk_level, item.fame_level), reverse=True):
        reason = row.risk_reason if row.risk_level == "高" else row.fame_reason
        lines.append(f"| {row.name} | {row.research_institute} | {reason} |")

    lines.extend([
        "",
        "## 全量总览",
        "",
        "| 姓名 | 研究所 | 推荐度 | 名气 | 风险度 | 新鲜度 | 方向归纳 | 最近关注 |",
        "|------|--------|--------|------|--------|--------|----------|----------|",
    ])
    for row in sorted(rows, key=lambda item: (item.final_score, item.recommendation), reverse=True):
        lines.append(
            f"| {row.name} | {row.research_institute} | {row.recommendation} | {row.fame_level} | "
            f"{row.risk_level} | {row.freshness} | {row.direction_summary} | {row.recent_focus} |"
        )

    lines.extend([
        "",
        "## 说明",
        "",
        "- 这份名单是 `Layer 2` 的投递优先级建议，不是最终定稿。",
        "- 真正发套磁前，主推荐名单仍应进入 `Layer 3`，检查最近两年论文、合作者和实际招生状态。",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 2 横向总览与推荐名单")
    parser.add_argument("--profiles-dir", required=True, help="Layer 2 画像目录")
    parser.add_argument("--output-md", required=True, help="Markdown 输出路径")
    parser.add_argument("--output-csv", required=True, help="CSV 输出路径")
    parser.add_argument("--max-per-institute", type=int, default=2, help="同一研究所最多保留多少位主投")
    args = parser.parse_args()

    profiles_dir = Path(args.profiles_dir)
    rows = [parse_profile(path) for path in sorted(profiles_dir.glob("*_profile.md"))]
    chosen, blocked = choose_primary_list(rows, max_per_institute=args.max_per_institute)
    backups = choose_backup_list(rows, chosen, blocked)
    assign_priority_buckets(rows, chosen, backups)

    output_md = Path(args.output_md)
    output_csv = Path(args.output_csv)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    write_csv(rows, output_csv)
    output_md.write_text(
        build_markdown(rows, chosen, backups, max_per_institute=args.max_per_institute),
        encoding="utf-8",
    )

    print(f"[保存] Markdown -> {output_md}")
    print(f"[保存] CSV -> {output_csv}")
    print(f"[主推荐] {len(chosen)} 位")
    print(f"[备选] {len(backups)} 位")


if __name__ == "__main__":
    main()
