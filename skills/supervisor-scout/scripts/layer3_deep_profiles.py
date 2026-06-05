#!/usr/bin/env python3
"""
Supervisor Scout — Layer 3 深度画像（MVP）
========================================
面向 Layer 2 主推荐名单，抓近 2 年论文、近期合作者和主页动态，
生成套磁前最终核验所需的深度画像。
"""

import argparse
import csv
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from layer2_batch_profiles import (
    CURRENT_YEAR,
    HEADERS,
    build_name_variants,
    build_scholar_queries,
    choose_openalex_queries,
    clean_text,
    contains_chinese,
    dedupe_keep_order,
    exact_name_match,
    extract_homepage_tables,
    extract_recent_homepage_items,
    fetch,
    infer_primary_themes,
    normalize_ascii_name,
    openalex_lookup,
    parse_author_names,
    parse_cited,
    parse_year,
    scholar_profile,
    scholar_search,
    split_directions,
    split_rep_items,
    topic_hit,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
DEEP_YEARS = {CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2}
BIT_TERMS = ["beijing institute of technology", "北京理工大学"]
SOCIAL_POSITIVE_KEYWORDS = ["神仙导师", "好导师", "推荐", "欢迎报考", "真诚的导师", "帮转", "值得推荐"]
SOCIAL_NEGATIVE_KEYWORDS = ["避雷", "慎选", "惹毛", "延毕", "压榨", "pua", "崩溃", "防火防盗防同门"]
STUDENT_FRIENDLY_KEYWORDS = ["优秀论文", "优秀毕业", "挑战杯", "互联网+", "指导学生", "优秀博士", "优秀硕士", "优秀毕业生", "一等奖", "金奖", "银奖"]
MENTOR_CONTEXT_KEYWORDS = ["导师", "老师", "课题组", "实验室", "组会", "学生", "博导", "硕导", "招生", "带学生"]
GROUP_SUPPORT_KEYWORDS = ["服务器", "算力", "实车平台", "数据集", "数据采集", "实验平台", "全方位", "科研支撑", "有力支撑"]
SOCIAL_GENERIC_NOISE_KEYWORDS = ["成绩", "学期", "宿舍", "保研", "本科", "大一", "考研经验", "新增列硕士生导师名单", "新增博导名单"]
PAPER_HINT_KEYWORDS = ["ieee", "journal", "transactions", "trans.", "学报", "automobile", "vehicle", "control", "规划", "无人", "车辆", "[j]", "[c]"]
NON_PAPER_KEYWORDS = ["专利", "项目", "基金", "主持", "副总师", "课题", "在研"]


def read_csv(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_target_rows(candidates_csv: str, overview_csv: str, names: List[str]) -> List[Dict]:
    candidates = read_csv(candidates_csv)
    by_name = {row["name"]: row for row in candidates}

    if names:
        selected = [by_name[name] for name in names if name in by_name]
        return selected

    overview_rows = read_csv(overview_csv)
    selected = []
    for row in overview_rows:
        if row.get("priority_bucket") == "主推荐" and row["name"] in by_name:
            selected.append(by_name[row["name"]])
    return selected


def strip_opencli_suffix(text: str) -> str:
    marker = "\n\n  Update available:"
    if marker in text:
        return text.split(marker, 1)[0].strip()
    return text.strip()


def run_opencli_json(args: List[str], timeout_sec: int = 60) -> List[Dict]:
    try:
        result = subprocess.run(
            args,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except Exception:
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        payload = strip_opencli_suffix(result.stdout)
        parsed = json.loads(payload)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def fetch_homepage_bundle(row: Dict) -> Dict:
    homepage = {"ok": False, "basic": {}, "sections": {}, "pub_date": "", "text": ""}
    try:
        response = fetch(row["profile_url"])
        soup = BeautifulSoup(response.text, "lxml")
        basic, sections, pub_date, page_text = extract_homepage_tables(soup)
        homepage = {"ok": True, "basic": basic, "sections": sections, "pub_date": pub_date, "text": page_text}
    except Exception:
        pass
    return homepage


def semantic_scholar_author_search(name: str, name_variants: List[str]) -> Dict:
    result = {
        "ok": False,
        "author_id": "",
        "name": "",
        "affiliations": [],
        "h_index": "",
        "paper_count": "",
        "citation_count": "",
        "papers": [],
        "note": "",
    }

    try:
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/author/search",
            headers=HEADERS,
            timeout=20,
            params={
                "query": name,
                "limit": 10,
                "fields": "name,affiliations,hIndex,paperCount,citationCount,url",
            },
        )
        response.raise_for_status()
    except Exception as exc:
        result["note"] = f"Semantic Scholar author search 失败: {exc}"
        return result

    best = None
    best_score = -1
    for item in response.json().get("data", []):
        display_name = clean_text(item.get("name", ""))
        affiliations = " ".join(clean_text(x) for x in item.get("affiliations") or [])
        score = 0
        if exact_name_match(name, display_name):
            score += 10
        if any(exact_name_match(variant, display_name) for variant in name_variants):
            score += 8
        if any(term in affiliations.lower() for term in BIT_TERMS):
            score += 20
        score += min(5, int((item.get("paperCount") or 0) / 20))
        if score > best_score:
            best = item
            best_score = score

    if not best:
        result["note"] = "未找到可靠的 Semantic Scholar 作者候选。"
        return result

    result["author_id"] = best.get("authorId", "")
    result["name"] = clean_text(best.get("name", ""))
    result["affiliations"] = [clean_text(x) for x in best.get("affiliations") or []]
    result["h_index"] = str(best.get("hIndex", "") or "")
    result["paper_count"] = str(best.get("paperCount", "") or "")
    result["citation_count"] = str(best.get("citationCount", "") or "")

    if not result["author_id"]:
        result["note"] = "命中候选但 authorId 为空。"
        return result

    try:
        papers_resp = requests.get(
            f"https://api.semanticscholar.org/graph/v1/author/{result['author_id']}/papers",
            headers=HEADERS,
            timeout=20,
            params={
                "limit": 100,
                "fields": "title,year,citationCount,venue,authors,url,externalIds",
            },
        )
        papers_resp.raise_for_status()
        raw_papers = papers_resp.json().get("data", [])
    except Exception as exc:
        result["note"] = f"Semantic Scholar papers 拉取失败: {exc}"
        return result

    seen = set()
    papers = []
    for item in raw_papers:
        title = clean_text(item.get("title", ""))
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        papers.append({
            "title": title,
            "year": item.get("year") or 0,
            "citation_count": item.get("citationCount") or 0,
            "venue": clean_text(item.get("venue", "")),
            "authors": [clean_text(author.get("name", "")) for author in item.get("authors") or [] if clean_text(author.get("name", ""))],
            "url": item.get("url", ""),
        })

    papers.sort(key=lambda item: (item["year"], item["citation_count"]), reverse=True)
    result["papers"] = papers
    result["ok"] = True
    result["note"] = "Semantic Scholar 作者与论文数据已获取。"
    return result


def search_social_signals(name: str, school_terms: List[str]) -> Dict:
    queries = dedupe_keep_order([
        f"{school_terms[0]} {name} 导师",
        f"{school_terms[1]} {name}",
    ])

    xiaohongshu_results: List[Dict] = []
    zhihu_results: List[Dict] = []
    for query in queries:
        if not xiaohongshu_results:
            xiaohongshu_results = run_opencli_json(
                ["opencli", "xiaohongshu", "search", "--limit", "6", "-f", "json", query],
                timeout_sec=90,
            )
        if not zhihu_results:
            zhihu_results = run_opencli_json(
                ["opencli", "zhihu", "search", "--limit", "6", "-f", "json", query],
                timeout_sec=90,
            )

    return {
        "xiaohongshu": xiaohongshu_results,
        "zhihu": zhihu_results,
        "douyin_note": "当前 opencli 的 douyin 适配器不提供通用关键词搜索，浏览器直连也不稳定，暂未纳入自动化结论。",
    }


def filter_recent_papers(papers: List[Dict], years: set) -> List[Dict]:
    filtered = [paper for paper in papers if (paper.get("year") or 0) in years]
    filtered.sort(key=lambda item: (item.get("year") or 0, item.get("citation_count") or 0), reverse=True)
    return filtered


def normalize_author_name(name: str) -> str:
    return re.sub(r"\s+", " ", clean_text(name)).lower()


def normalize_title_key(title: str) -> str:
    return normalize_ascii_name(title) or re.sub(r"\s+", "", clean_text(title)).lower()


def has_target_author(name: str, name_variants: List[str], authors: List[str]) -> bool:
    def ascii_person_name_matches(variant: str, author: str) -> bool:
        variant_parts = normalize_ascii_name(variant).split()
        author_parts = normalize_ascii_name(author).split()
        if not variant_parts or not author_parts:
            return False
        if variant_parts == author_parts:
            return True
        if len(variant_parts) == 2 and len(author_parts) == 2:
            return (
                (variant_parts[0][0] == author_parts[0][0] and variant_parts[1] == author_parts[1]) or
                (variant_parts[1][0] == author_parts[0][0] and variant_parts[0] == author_parts[1]) or
                (variant_parts[0] == author_parts[0] and variant_parts[1][0] == author_parts[1][0]) or
                (variant_parts[1] == author_parts[0] and variant_parts[0][0] == author_parts[1][0])
            )
        return False

    for author in authors:
        if exact_name_match(name, author):
            return True
        for variant in name_variants:
            if ascii_person_name_matches(variant, author):
                return True
    return False


def scholar_item_has_target_author(name: str, name_variants: List[str], item: Dict) -> bool:
    authors = parse_author_names(clean_text(item.get("meta", "")))
    return has_target_author(name, name_variants, authors)


def extract_structured_homepage_recent_papers(section_text: str) -> List[Dict]:
    text = clean_text(section_text)
    if not text:
        return []

    prepared = re.sub(r"(\[\s*\d+\s*\]|\(\d+\))", r"\n\1", text)
    prepared = re.sub(r"(?<!\d)(\d+\.)\s*(?=[A-Za-z\u4e00-\u9fff])", r"\n\1 ", prepared)
    segments = [clean_text(part) for part in prepared.splitlines() if clean_text(part)]

    papers = []
    seen = set()
    for segment in segments:
        year = parse_year(segment)
        if not year or year not in DEEP_YEARS:
            continue

        lowered = segment.lower()
        if any(keyword in segment for keyword in NON_PAPER_KEYWORDS):
            continue
        if re.search(r"20\d{2}\.\d+\s*[至-]\s*20\d{2}\.\d+", segment):
            continue
        if not any(keyword in lowered for keyword in PAPER_HINT_KEYWORDS) and not any(
            keyword in segment for keyword in ["无人", "车辆", "电机", "电池", "轨迹", "控制"]
        ):
            continue

        title = re.sub(r"^(近五年\d+篇论文代表作:|代表性论文:?|一、\s*代表性论文)\s*", "", segment)
        title = re.sub(r"^[\[\(]?\s*\d+\s*[\]\)]?\.?\s*", "", title)
        title = clean_text(title)
        key = normalize_title_key(title)
        if not title or key in seen:
            continue
        seen.add(key)
        papers.append({
            "title": title,
            "year": year,
            "venue": "主页代表作/近年成果",
            "authors": [],
            "citation_count": 0,
            "source": "homepage",
            "confidence": 4,
        })

    papers.sort(key=lambda item: (item["year"], item["confidence"]), reverse=True)
    return papers[:8]


def extract_reliable_scholar_recent_papers(row: Dict, scholar: Dict) -> List[Dict]:
    name_variants = build_name_variants(row["name"])
    papers = []
    for item in scholar.get("items", []):
        year = item.get("year") or 0
        if year not in DEEP_YEARS or not scholar_item_has_target_author(row["name"], name_variants, item):
            continue
        authors = parse_author_names(clean_text(item.get("meta", "")))
        venue = clean_text(item.get("meta", "").split("-", 1)[1]) if "-" in clean_text(item.get("meta", "")) else "Scholar"
        papers.append({
            "title": clean_text(item.get("title", "")),
            "year": year,
            "venue": venue or "Scholar",
            "authors": authors,
            "citation_count": item.get("cited") or 0,
            "source": "scholar",
            "confidence": 5 if topic_hit(item.get("title", ""), row.get("direction_keywords", "")) else 4,
        })
    return papers


def extract_reliable_semantic_recent_papers(row: Dict, semantic: Dict) -> List[Dict]:
    if not semantic.get("ok") or not exact_name_match(row["name"], semantic.get("name", "")):
        return []

    name_variants = build_name_variants(row["name"])
    affiliation_text = " ".join(clean_text(x) for x in semantic.get("affiliations") or []).lower()
    has_bit_affiliation = any(term in affiliation_text for term in BIT_TERMS)

    papers = []
    for paper in filter_recent_papers(semantic.get("papers", []), DEEP_YEARS):
        authors = [clean_text(author) for author in paper.get("authors", []) if clean_text(author)]
        if not has_target_author(row["name"], name_variants, authors):
            continue
        title = clean_text(paper.get("title", ""))
        venue = clean_text(paper.get("venue", ""))
        if not (has_bit_affiliation or topic_hit(title, row.get("direction_keywords", "")) or "bit" in venue.lower()):
            continue
        papers.append({
            "title": title,
            "year": paper.get("year") or 0,
            "venue": venue or "Semantic Scholar",
            "authors": authors,
            "citation_count": paper.get("citation_count") or 0,
            "source": "semantic",
            "confidence": 6 if has_bit_affiliation else 5,
        })
    return papers


def merge_recent_papers(*paper_groups: List[Dict]) -> List[Dict]:
    merged = []
    seen = set()
    for group in paper_groups:
        for paper in group:
            key = normalize_title_key(paper.get("title", ""))
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(paper)
    merged.sort(
        key=lambda item: (
            item.get("year") or 0,
            item.get("confidence") or 0,
            item.get("citation_count") or 0,
        ),
        reverse=True,
    )
    return merged[:12]


def extract_recent_collaborators(name: str, papers: List[Dict]) -> List[Tuple[str, int]]:
    target = normalize_author_name(name)
    counter = Counter()
    display_names: Dict[str, str] = {}
    for paper in papers:
        seen = set()
        for author in paper.get("authors", []):
            author_norm = normalize_author_name(author)
            if not author_norm or author_norm == target or author_norm in seen:
                continue
            seen.add(author_norm)
            counter[author_norm] += 1
            if author_norm not in display_names or (
                contains_chinese(author) and not contains_chinese(display_names[author_norm])
            ) or len(author) > len(display_names[author_norm]):
                display_names[author_norm] = author
    return [(display_names[key], count) for key, count in counter.most_common(8)]


def extract_scholar_recent_collaborators(name: str, scholar_items: List[Dict]) -> List[Tuple[str, int]]:
    target = normalize_author_name(name)
    counter = Counter()
    for item in scholar_items:
        meta = clean_text(item.get("meta", ""))
        authors = parse_author_names(meta)
        seen = set()
        for author in authors:
            author_norm = normalize_author_name(author)
            if not author_norm or author_norm == target or author_norm in seen:
                continue
            seen.add(author_norm)
            counter[author] += 1
    return counter.most_common(8)


def analyze_social_results(name: str, school_terms: List[str], social_data: Dict) -> Dict:
    def classify_sentiment(title: str) -> str:
        if any(keyword in title for keyword in SOCIAL_NEGATIVE_KEYWORDS):
            return "negative"
        if any(keyword in title for keyword in SOCIAL_POSITIVE_KEYWORDS):
            return "positive"
        return "neutral"

    direct_entries = []
    contextual_entries = []
    generic_school_hits = 0
    for platform in ["xiaohongshu", "zhihu"]:
        for item in social_data.get(platform, []):
            title = clean_text(str(item.get("title", "")))
            if not title:
                continue
            direct = name in title
            school_related = any(term in title for term in school_terms)
            mentor_related = any(keyword in title for keyword in MENTOR_CONTEXT_KEYWORDS)
            generic_noise = any(keyword in title for keyword in SOCIAL_GENERIC_NOISE_KEYWORDS)
            if not direct and not school_related:
                continue
            entry = {
                "platform": platform,
                "title": title,
                "author": clean_text(str(item.get("author", ""))),
                "url": item.get("url", ""),
                "direct": direct,
                "school_related": school_related,
                "mentor_related": mentor_related,
                "sentiment": classify_sentiment(title),
            }
            if direct:
                direct_entries.append(entry)
            elif mentor_related and not generic_noise:
                contextual_entries.append(entry)
            else:
                generic_school_hits += 1

    positive_hits = [entry for entry in direct_entries if entry["sentiment"] == "positive"]
    negative_hits = [entry for entry in direct_entries if entry["sentiment"] == "negative"]

    if negative_hits:
        summary = "检到少量直接相关的负面题名，值得人工点开复核，但绝不能直接当事实。"
    elif positive_hits:
        summary = "检到少量直接相关的正向题名，但样本量不大，只能当弱信号。"
    elif direct_entries:
        summary = "有直接相关题名，但情绪倾向并不明确，更适合作为人工复核线索。"
    elif contextual_entries:
        summary = "平台上有院系层面的导师讨论，但没有稳定点名到这位老师，只能当外围语境。"
    elif generic_school_hits:
        summary = "平台上检到一些学校泛帖，但已从个人判断中剔除。"
    else:
        summary = "当前没有检到足够相关的公开学生讨论。"

    return {
        "summary": summary,
        "entries": (direct_entries + contextual_entries)[:8],
        "direct_hits": len(direct_entries),
        "positive_hits": len(positive_hits),
        "negative_hits": len(negative_hits),
        "contextual_hits": len(contextual_entries),
        "generic_school_hits": generic_school_hits,
        "douyin_note": social_data.get("douyin_note", ""),
    }


def infer_homepage_activity(homepage: Dict, homepage_recent: List[Dict]) -> Tuple[str, str]:
    years = [parse_year(homepage.get("pub_date", ""))]
    years.extend(parse_year(item.get("year", "")) for item in homepage_recent)
    years = [year for year in years if year]
    if not years:
        return "未知", "主页未明确提供可判定的更新时间。"
    latest_year = max(years)
    if latest_year >= CURRENT_YEAR - 1:
        return "较活跃", f"主页或主页代表作至少更新到 {latest_year} 年。"
    if latest_year >= CURRENT_YEAR - 3:
        return "一般", f"主页最近可见更新约到 {latest_year} 年。"
    return "偏旧", f"主页最近可见更新仅到 {latest_year} 年。"


def collect_recent_project_signals(sections: Dict[str, str]) -> List[str]:
    signals = []
    for key in ["代表性论文及项目", "成果及荣誉", "社会职务", "简介与研究方向"]:
        text = clean_text(sections.get(key, ""))
        if not text:
            continue
        parts = re.split(r"(?<=。)|(?<=；)|(?<=\])", text)
        for part in parts:
            part = clean_text(part)
            year = parse_year(part)
            if year and year >= CURRENT_YEAR - 2:
                signals.append(part)
    return dedupe_keep_order(signals)[:8]


def collect_student_friendly_signals(
    sections: Dict[str, str],
    collaborators: List[Tuple[str, int]],
    social_summary: Dict,
    homepage_activity: str,
) -> Dict:
    signals: List[Tuple[str, str]] = []
    intro = clean_text(" ".join([sections.get("简介与研究方向", ""), sections.get("研究方向", "")]))
    honors = clean_text(sections.get("成果及荣誉", ""))
    social = clean_text(sections.get("社会职务", ""))
    evidence_score = 0

    if collaborators and collaborators[0][1] >= 2:
        signals.append(("近年合作者连续性", f"近两年重复出现的共同作者比较明显，例如 {collaborators[0][0]} 已共同出现 {collaborators[0][1]} 次。"))
        evidence_score += 2
    else:
        signals.append(("近年合作者连续性", "近期共同作者有公开信号，但还看不出特别清晰的稳定学生梯队。"))

    student_honors = [kw for kw in STUDENT_FRIENDLY_KEYWORDS if kw in f"{honors} {intro}"]
    if student_honors:
        signals.append(("学生培养公开成果", f"主页里能看到学生培养类关键词：{'、'.join(dedupe_keep_order(student_honors)[:4])}。"))
        evidence_score += 2
    else:
        signals.append(("学生培养公开成果", "主页没有明显写出优秀论文、竞赛获奖或学生去向，公开透明度一般。"))

    if any(keyword in intro for keyword in ["欢迎", "报考", "加入", "招收"]):
        signals.append(("公开招收态度", "主页存在欢迎报考/加入课题组等表达，至少说明对外表达较开放。"))
        evidence_score += 1
    else:
        signals.append(("公开招收态度", "主页没有明显的欢迎报考表述，不能据此下负面判断，只能说公开信号偏少。"))

    support_keywords = [kw for kw in GROUP_SUPPORT_KEYWORDS if kw in intro]
    if support_keywords:
        signals.append(("组内资源支持", f"主页明确提到课题组资源支持，如 {'、'.join(dedupe_keep_order(support_keywords)[:3])}。"))
        evidence_score += 1
    else:
        signals.append(("组内资源支持", "主页没有明确展开算力、数据或实车平台支持，资源条件仍需进一步私下核验。"))

    if any(keyword in social for keyword in ["副院长", "所长", "主任"]):
        signals.append(("精力分配风险", "公开职务较多，后续要重点核验实际带学生精力和沟通频率。"))
    else:
        signals.append(("精力分配风险", "暂未看到特别重的行政职务信号。"))

    if homepage_activity == "偏旧" and not student_honors:
        signals.append(("信息透明度", "主页偏旧且学生培养公开记录不多，之后最好通过论文作者、在读学生或学长学姐再核一次。"))
    elif homepage_activity == "偏旧":
        signals.append(("信息透明度", "主页偏旧，但仍能看到少量学生培养公开记录，说明线上信息不新但不至于完全失真。"))
        evidence_score += 1
    else:
        signals.append(("信息透明度", "主页近年仍有更新或近年成果可见，做初筛时的信息透明度相对更好。"))
        evidence_score += 1

    signals.append(("学生讨论弱信号", social_summary["summary"]))
    if social_summary["negative_hits"]:
        evidence_score -= 1

    if evidence_score >= 5:
        level = "中等偏强"
        summary = "公开来源里不只看到方向和论文，还能看到部分培养记录或组内支持条件。"
    elif evidence_score >= 3:
        level = "中等"
        summary = "能看到一些学生培养或组内支持信号，但离下结论还差直接学生反馈。"
    else:
        level = "偏弱"
        summary = "目前更多还是间接公开信号，判断老师是否真正带学生顺手，证据仍不够硬。"

    return {"level": level, "summary": summary, "items": signals}


def build_deep_judgement(
    row: Dict,
    recent_paper_count: int,
    recent_collabs: List[Tuple[str, int]],
    homepage_activity: str,
    recent_focus: str,
) -> Tuple[str, str, str]:
    if recent_paper_count == 0:
        return (
            "谨慎推进",
            "近两年论文抓取不足，先不要直接把这位老师作为套磁首选。",
            "先补抓近两年论文全量和实际学生/博后作者，再决定是否联系。",
        )

    if recent_paper_count >= 4 and homepage_activity != "偏旧":
        return (
            "可以优先推进",
            f"近两年公开论文信号连续，近期主题集中在 {recent_focus}，具备继续进入套磁准备的价值。",
            "进入具体读文阶段，挑 2-3 篇最近论文做切入点，核验合作者里是否已有稳定学生梯队。",
        )

    return (
        "可推进但需补核验",
        f"近两年已经能看到一定论文信号，方向上仍延续到 {recent_focus}，但还不够支撑直接下最终判断。",
        "联系前先补核验近两年论文是否基本抓全，以及近期合作者是否体现稳定招生活动。",
    )


def resolve_direction_summary(row: Dict, sections: Dict[str, str]) -> str:
    raw = clean_text(sections.get("研究方向", ""))
    if raw and len(raw) <= 80:
        directions = split_directions(raw)
        if directions:
            return "；".join(directions[:3])
        return raw
    return row.get("direction_keywords", "待补充")


def build_deep_profile(
    row: Dict,
    homepage: Dict,
    scholar: Dict,
    scholar_prof: Dict,
    openalex: Dict,
    semantic: Dict,
    social_data: Dict,
) -> str:
    sections = homepage.get("sections", {})
    basic = homepage.get("basic", {})
    intro = sections.get("简介与研究方向") or sections.get("教育及工作经历") or "待补充"
    directions = split_directions(sections.get("研究方向") or row.get("direction_keywords", ""))
    rep_items = split_rep_items(sections.get("代表性论文及项目", ""))
    homepage_recent = extract_recent_homepage_items(rep_items)
    homepage_recent_papers = extract_structured_homepage_recent_papers(sections.get("代表性论文及项目", ""))
    scholar_recent_papers = extract_reliable_scholar_recent_papers(row, scholar)
    semantic_recent_papers = extract_reliable_semantic_recent_papers(row, semantic)
    recent_papers = merge_recent_papers(homepage_recent_papers, scholar_recent_papers, semantic_recent_papers)
    recent_items = [{"title": paper["title"], "year": paper["year"], "source": paper["source"]} for paper in recent_papers]
    if openalex.get("valid"):
        for item in openalex.get("recent_works", [])[:3]:
            recent_items.append({
                "title": clean_text(item.get("title", "")),
                "year": parse_year(item.get("year", "")) or 0,
                "source": "openalex",
            })
    themes = infer_primary_themes(row, directions, intro, recent_items)
    recent_focus = "、".join(theme["label"] for theme in themes) if themes else row.get("direction_keywords", "待补充")

    collaborators = extract_recent_collaborators(row["name"], scholar_recent_papers + semantic_recent_papers)
    social_summary = analyze_social_results(row["name"], ["北京理工大学", "北理"], social_data)
    homepage_activity, homepage_activity_note = infer_homepage_activity(homepage, homepage_recent)
    project_signals = collect_recent_project_signals(sections)
    recent_paper_count = len(recent_papers)
    judgement, reason, action = build_deep_judgement(row, recent_paper_count, collaborators, homepage_activity, recent_focus)
    student_friendly = collect_student_friendly_signals(sections, collaborators, social_summary, homepage_activity)

    lines = [
        f"# {row['name']} — Layer 3 深度画像",
        "",
        f"> **生成时间**: {CURRENT_DATE}",
        "> **层级**: Layer 3（套磁前最终核验）",
        "> **核心原则**: 优先看最近 2 年实际论文和近期合作者，而不是只看主页标签。",
        "",
        "## 基本信息",
        "",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 姓名 | {row['name']} |",
        f"| 研究所 | {row.get('research_institute', '待补充')} |",
        f"| 学院/专业 | {basic.get('学院专业') or basic.get('学院') or row.get('college', '待补充')} |",
        f"| 职称等级 | {row.get('title_rank', '待补充')} |",
        f"| 主页链接 | {row.get('profile_url', '待补充')} |",
        "",
        "## 最终判断",
        "",
        f"- **是否建议进入实际套磁准备**: {judgement}",
        f"- **主要理由**: {reason}",
        f"- **下一步动作**: {action}",
        "",
        "## 近期主题与演化",
        "",
        f"- **主页写法**: {resolve_direction_summary(row, sections)}",
        f"- **近两年实际信号**: {recent_focus}",
    ]

    if recent_items:
        lines.append(f"- **近期公开主轴**: {'；'.join(item['title'] for item in recent_items[:3])}")

    lines.extend([
        "",
        "## 近 2 年论文",
        "",
    ])
    if recent_papers:
        for paper in recent_papers[:12]:
            venue = paper.get("venue", "期刊/会议待补充")
            authors = "，".join(paper.get("authors", [])[:6]) or "作者待补充"
            lines.append(
                f"- `{paper.get('year', '')}` {paper.get('title', '')} | {venue} | 引用 {paper.get('citation_count', 0)} | 作者: {authors}"
            )
    else:
        lines.append("- 近两年论文未稳定抓全，当前仍需要人工补核。")

    lines.extend([
        "",
        "## 近期合作者",
        "",
    ])
    if collaborators:
        for author, count in collaborators:
            lines.append(f"- **{author}**: 近两年共同出现 {count} 次")
    else:
        lines.append("- 暂未从结构化论文源中稳定提取到近两年合作者。")

    lines.extend([
        "",
        "## 主页与项目动态",
        "",
        f"- **主页活跃度**: {homepage_activity}",
        f"- **活跃度说明**: {homepage_activity_note}",
    ])
    if project_signals:
        lines.append("- **近年项目/公开动态**:")
        for signal in project_signals[:6]:
            lines.append(f"  - {signal}")
    else:
        lines.append("- **近年项目/公开动态**: 主页没有明确提供足够新的动态片段。")

    lines.extend([
        "",
        "## 学生友好度观察",
        "",
        f"- **证据等级**: {student_friendly['level']}。{student_friendly['summary']}",
    ])
    for title, note in student_friendly["items"]:
        lines.append(f"- **{title}**: {note}")

    lines.extend([
        "",
        "## 社交平台弱信号",
        "",
        f"- **总体判断**: {social_summary['summary']}",
        f"- **小红书/知乎直接点名样本数**: {social_summary['direct_hits']}（正向 {social_summary['positive_hits']} / 需复核负向 {social_summary['negative_hits']}）",
        f"- **院系层面导师讨论**: {social_summary['contextual_hits']} 条；学校泛帖已剔除 {social_summary['generic_school_hits']} 条",
        f"- **抖音**: {social_summary['douyin_note']}",
    ])
    if social_summary["entries"]:
        lines.append("- **可回看线索**:")
        for entry in social_summary["entries"][:5]:
            lines.append(
                f"  - [{entry['platform']}] {entry['title']} | {entry['author']} | {'直接点名' if entry['direct'] else '学校相关'}"
            )
    else:
        lines.append("- **可回看线索**: 暂未检到足够相关的公开帖子。")

    lines.extend([
        "",
        "## 数据源核验",
        "",
        f"- **Google Scholar 结果页**: {'已获取' if scholar.get('items') else '未稳定获取'}",
        f"- **Google Scholar Profile**: {scholar_prof.get('name', '未命中可靠 profile')}",
        f"- **OpenAlex**: {openalex.get('author_name', '未可靠命中')} / {openalex.get('match_note', '未使用')}",
        f"- **Semantic Scholar**: {semantic.get('name', '未可靠命中')} / {semantic.get('note', '未使用')}{'；未通过论文主判断校验' if semantic.get('ok') and not semantic_recent_papers else ''}",
        f"- **小红书**: {'已搜索' if social_data.get('xiaohongshu') else '未命中或未执行'}",
        f"- **知乎**: {'已搜索' if social_data.get('zhihu') else '未命中或未执行'}",
        "",
        "## 套磁提示",
        "",
        "- 真正写邮件前，建议从上面的近两年论文里挑 2 篇最贴近你背景的文章精读。",
        "- 如果近期合作者里反复出现年轻作者，通常比主页标签更能说明组里最近确实在带学生。",
        "- 若主页活跃度偏旧，但近两年论文连续，不应仅凭主页过时就降权；反过来亦然。",
    ])

    return "\n".join(lines)


def generate_one(row: Dict, output_dir: str) -> Tuple[str, Dict]:
    homepage = fetch_homepage_bundle(row)
    name_variants = build_name_variants(row["name"])
    scholar = scholar_search(build_scholar_queries(row), row["name"], name_variants, row.get("direction_keywords", ""))

    scholar_prof = {}
    if scholar.get("profile_url") and (
        exact_name_match(row["name"], scholar.get("profile_name", "")) or any(
            exact_name_match(variant, scholar.get("profile_name", "")) for variant in name_variants
        )
    ):
        try:
            scholar_prof = scholar_profile(scholar["profile_url"])
        except Exception:
            scholar_prof = {}

    openalex_queries = choose_openalex_queries(row["name"], scholar_prof.get("name", ""), homepage.get("text", ""))
    try:
        openalex = openalex_lookup(openalex_queries, row.get("direction_keywords", ""), row["name"], name_variants)
    except Exception:
        openalex = {"author_name": "", "valid": False, "match_note": "OpenAlex 查询失败。", "recent_works": []}

    semantic = semantic_scholar_author_search(row["name"], name_variants)
    social_data = search_social_signals(row["name"], ["北京理工大学", "北理"])
    profile_text = build_deep_profile(row, homepage, scholar, scholar_prof, openalex, semantic, social_data)

    output_path = os.path.join(output_dir, f"{row['name']}_deep.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(profile_text)

    status = {
        "homepage": homepage["ok"],
        "scholar": bool(scholar.get("items")),
        "scholar_profile": bool(scholar_prof.get("name")),
        "openalex": bool(openalex.get("valid")),
        "semantic": bool(extract_reliable_semantic_recent_papers(row, semantic)),
        "social": bool(social_data.get("xiaohongshu") or social_data.get("zhihu")),
        "output_path": output_path,
    }
    return output_path, status


def write_batch_report(rows: List[Dict], statuses: Dict[str, Dict], output_dir: str) -> None:
    lines = [
        "# Layer 3 批量生成报告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**生成人数**: {len(rows)}",
        "",
        "| 姓名 | 主页 | Scholar | Scholar Profile | OpenAlex | Semantic Scholar | 社交平台 | 输出文件 |",
        "|------|------|---------|-----------------|----------|------------------|----------|----------|",
    ]
    for row in rows:
        status = statuses[row["name"]]
        lines.append(
            f"| {row['name']} | {'✅' if status['homepage'] else '⚠️'} | "
            f"{'✅' if status['scholar'] else '⚠️'} | "
            f"{'✅' if status['scholar_profile'] else '⚠️'} | "
            f"{'✅' if status['openalex'] else '⚠️'} | "
            f"{'✅' if status['semantic'] else '⚠️'} | "
            f"{'✅' if status['social'] else '⚠️'} | "
            f"`{os.path.basename(status['output_path'])}` |"
        )
    Path(output_dir, "BATCH_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 3 深度画像（MVP）")
    parser.add_argument("--candidates-csv", required=True, help="Layer 1 A 候选 CSV")
    parser.add_argument("--overview-csv", help="Layer 2 总览 CSV；若不给名字则默认从这里取主推荐")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--names", nargs="*", help="指定导师姓名；为空时从 overview-csv 读取主推荐")
    args = parser.parse_args()

    if not args.names and not args.overview_csv:
        parser.error("未提供 --names 时必须提供 --overview-csv")

    rows = load_target_rows(args.candidates_csv, args.overview_csv or "", args.names or [])
    if not rows:
        raise SystemExit("未找到可生成的 Layer 3 目标导师。")

    os.makedirs(args.output_dir, exist_ok=True)
    statuses: Dict[str, Dict] = {}
    for row in rows:
        output_path, status = generate_one(row, args.output_dir)
        statuses[row["name"]] = status
        print(f"[保存] {row['name']} -> {output_path}")

    write_batch_report(rows, statuses, args.output_dir)
    print(f"[完成] Layer 3 深度画像 {len(rows)} 位")


if __name__ == "__main__":
    main()
