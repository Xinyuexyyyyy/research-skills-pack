#!/usr/bin/env python3
"""
Supervisor Scout — Layer 2 批量画像生成（多源增强版）
====================================================
Layer 2 必须是多源浅层画像：
- 官方主页：静态身份、联系方式、旧版方向、可能的代表作
- Google Scholar：近期论文信号，必要时作为主 freshness 源
- OpenAlex：仅在作者与机构都可靠匹配时补充指标和近期 works
"""

import argparse
import csv
import os
import re
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

try:
    from pypinyin import lazy_pinyin
except Exception:
    lazy_pinyin = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CURRENT_YEAR = datetime.now().year

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

SCHOLAR_BASES = [
    "https://scholar.lanfanshu.cn",
    "https://scholar.google.com",
]

SPECIAL_NOTES = {
    "项昌乐": "已调任大连理工大学党委书记，需在联系前确认是否仍在北理招生。",
    "陈慧岩": "1961年生，接近退休，需确认近年是否持续招生。",
    "何洪文": "担任研究生院副院长，行政事务较多，需确认指导精力与招生活跃度。",
    "孙逢春": "院士，团队规模大，适合后续进入 Layer 3 深度画像。",
    "熊瑞": "高被引学者，近期方向演进明显，后续适合优先进入 Layer 3。",
}

SECTION_ALIASES = {
    "个人简介与研究方向": "简介与研究方向",
    "教育及工作经历": "教育及工作经历",
    "主要研究方向": "研究方向",
    "研究方向": "研究方向",
    "代表性论文": "代表性论文及项目",
    "代表性论文及研究项目": "代表性论文及项目",
    "代表性论著及研究项目": "代表性论文及项目",
    "成果及荣誉": "成果及荣誉",
    "成果及社会服务": "成果及荣誉",
    "社会职务": "社会职务",
}

DOMAIN_KEYWORDS = [
    "battery", "vehicle", "electric", "energy", "transportation", "automotive",
    "driving", "rover", "motor", "gearbox", "nvh", "acoustic", "vibration",
    "suspension", "autonomous", "control", "pack", "charge", "thermal",
    "无人", "智能", "电池", "车辆", "汽车", "电动", "能量", "传动",
    "噪声", "振动", "地面", "自动驾驶", "热管理", "充电", "安全",
]

THEME_BUCKETS = [
    {
        "key": "battery",
        "label": "动力电池 / 电池管理",
        "keywords": ["battery", "lithium", "soc", "soh", "析锂", "电池", "充电", "热管理", "安全", "bms", "寿命"],
        "assessment": "方向热度高、产业需求强，适合做电池建模、状态估计、安全和寿命问题；缺点是实验平台、数据和验证门槛较高。",
    },
    {
        "key": "energy",
        "label": "整车能量管理 / 混动控制",
        "keywords": ["energy management", "hybrid", "phev", "hev", "fuel cell", "增程", "混合动力", "燃料电池", "能量管理", "制动能量回收"],
        "assessment": "方向应用导向强，容易和整车控制、交通工况、强化学习结合；优点是工程问题明确，缺点是创新点需要和算法或系统平台结合才能拉开差距。",
    },
    {
        "key": "intelligent",
        "label": "智能车辆 / 自动驾驶",
        "keywords": ["autonomous", "planning", "decision", "control", "point cloud", "智能", "自动驾驶", "感知", "规划", "决策", "轨迹", "路径"],
        "assessment": "方向很热，论文空间大，但竞争也最激烈；适合算法和系统能力都强、愿意做仿真与实车闭环的人。",
    },
    {
        "key": "special",
        "label": "特种车辆 / 无人平台",
        "keywords": ["tracked", "ugv", "special vehicle", "terrain", "特种", "履带", "无人平台", "地面无人", "越野", "装备车辆"],
        "assessment": "方向偏硬核工程与装备平台，课题壁垒高、资源约束强；适合想做系统工程、底盘平台和实际装备问题的人。",
    },
    {
        "key": "transmission",
        "label": "传动系统 / 车辆动力学 / NVH",
        "keywords": ["transmission", "gearbox", "vibration", "suspension", "nvh", "传动", "振动", "悬架", "动力学", "减振", "声源"],
        "assessment": "方向偏机械系统和机理，课题相对扎实，适合做模型、试验和结构优化；缺点是纯算法型高热度不如智能驾驶和电池。",
    },
]

RECENT_TOPIC_BUCKETS = [
    {"label": "电池状态估计", "keywords": ["soc", "soh", "state of charge", "state of health", "状态估计"]},
    {"label": "电池安全与热管理", "keywords": ["thermal", "short circuit", "安全", "热", "外部短路", "热失控"]},
    {"label": "析锂与寿命机理", "keywords": ["析锂", "plating", "lifetime", "degradation", "寿命"]},
    {"label": "混动/增程能量管理", "keywords": ["energy management", "hybrid", "增程", "混合动力", "制动", "ecms"]},
    {"label": "强化学习/智能控制", "keywords": ["reinforcement learning", "deep learning", "imitation learning", "学习", "神经网络"]},
    {"label": "智能驾驶规划控制", "keywords": ["planning", "trajectory", "autonomous", "point cloud", "自动驾驶", "规划", "决策"]},
    {"label": "车辆动力学与稳定性", "keywords": ["stability", "yaw", "dynamics", "动力学", "稳定性"]},
    {"label": "传动振动与NVH", "keywords": ["torsional", "vibration", "gearbox", "nvh", "减振", "振动", "传动"]},
    {"label": "特种/无人平台", "keywords": ["ugv", "tracked", "terrain", "特种", "无人平台", "履带", "越野"]},
]

BIT_INSTITUTION_KEYWORDS = [
    "beijing institute of technology",
    "北京理工大学",
]

DOUBLE_SURNAMES = {
    "欧阳", "司马", "上官", "夏侯", "诸葛", "东方", "尉迟", "公孙", "皇甫",
    "慕容", "令狐", "长孙", "宇文", "司徒", "司空", "独孤", "南宫",
}


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_label(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def normalize_ascii_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean_text(text).lower()).strip()


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


NORMALIZED_SECTION_ALIASES = {normalize_label(k): v for k, v in SECTION_ALIASES.items()}
NORMALIZED_HEADING_KEYS = set(NORMALIZED_SECTION_ALIASES)


def read_candidates(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fetch(url: str, timeout: int = 20, params: Optional[Dict] = None) -> requests.Response:
    response = requests.get(url, headers=HEADERS, timeout=timeout, params=params)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response


def exact_name_match(target: str, found: str) -> bool:
    target = clean_text(target)
    found = clean_text(found)
    if not target or not found:
        return False
    if contains_chinese(target):
        return target in found
    t = normalize_ascii_name(target)
    f = normalize_ascii_name(found)
    return t == f or t in f or f in t


def build_name_variants(name: str) -> List[str]:
    name = clean_text(name)
    if not name:
        return []
    if not contains_chinese(name):
        return [name]
    if lazy_pinyin is None:
        return []

    surname_len = 2 if len(name) >= 2 and name[:2] in DOUBLE_SURNAMES else 1
    surname = "".join(lazy_pinyin(name[:surname_len])).title()
    given = "".join(lazy_pinyin(name[surname_len:])).title()
    variants = []
    if surname and given:
        variants.extend([f"{surname} {given}", f"{given} {surname}"])
    elif surname:
        variants.append(surname)
    return dedupe_keep_order(variants)


def dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        key = clean_text(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def parse_author_names(meta: str) -> List[str]:
    meta = clean_text(meta)
    if not meta:
        return []
    author_part = meta.split("-", 1)[0]
    author_part = author_part.replace(" and ", ", ")
    parts = re.split(r"[;,，、·]| \.\.\. ", author_part)
    return [clean_text(part) for part in parts if clean_text(part)]


def is_relevant_author_text(text: str, target_name: str, name_variants: List[str]) -> bool:
    text = clean_text(text)
    if not text:
        return False
    if contains_chinese(target_name) and target_name in text:
        return True
    for variant in name_variants:
        if exact_name_match(variant, text):
            return True
    return False


def contains_bit_institution(text: str) -> bool:
    haystack = clean_text(text).lower()
    return any(keyword in haystack for keyword in BIT_INSTITUTION_KEYWORDS)


def extract_homepage_tables(soup: BeautifulSoup) -> Tuple[Dict[str, str], Dict[str, str], str, str]:
    basic: Dict[str, str] = {}
    sections: Dict[str, str] = {}

    pub_meta = soup.find("meta", attrs={"name": "PubDate"})
    pub_date = clean_text(pub_meta.get("content")) if pub_meta else ""

    for table in soup.select("table"):
        for tr in table.select("tr"):
            cells = [clean_text(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            cells = [cell for cell in cells if cell]
            if not cells:
                continue

            if len(cells) == 1:
                cell = cells[0]
                norm = normalize_label(cell)
                if norm in NORMALIZED_HEADING_KEYS:
                    sections.setdefault(NORMALIZED_SECTION_ALIASES[norm], "")
                elif sections:
                    last_key = list(sections.keys())[-1]
                    if not sections[last_key]:
                        sections[last_key] = cell
                continue

            head = cells[0]
            norm_head = normalize_label(head)
            if norm_head in NORMALIZED_HEADING_KEYS:
                sections[NORMALIZED_SECTION_ALIASES[norm_head]] = " ".join(cells[1:]).strip()
                continue

            if norm_head == "姓名":
                basic["姓名"] = cells[1]
            elif norm_head == "职称":
                basic["职称"] = " ".join(cells[1:])
            elif norm_head == "学院":
                basic["学院"] = " ".join(cells[1:])
            elif norm_head in {"专业", "学院专业", "学院及专业"}:
                basic["学院专业"] = " ".join(cells[1:])
            elif norm_head == "办公地址":
                basic["办公地址"] = " ".join(cells[1:])
            elif norm_head == "邮编":
                basic["邮编"] = " ".join(cells[1:])
            elif norm_head in {"办公电话", "电话"}:
                basic["办公电话"] = " ".join(cells[1:])
            elif norm_head in {"邮件", "邮箱", "email", "e-mail"}:
                basic["邮箱"] = " ".join(cells[1:])
            elif len(cells) == 2 and len(head) <= 8:
                basic[head] = cells[1]

    page_text = clean_text(soup.get_text(" ", strip=True))
    return basic, sections, pub_date, page_text


def split_directions(text: str) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    normalized = text.replace("；", ";").replace("。", ";").replace("，", ",")
    parts = re.split(r"[;；]", normalized)
    results = []
    for part in parts:
        part = clean_text(part)
        if part:
            results.append(part)
    return results[:5]


def split_rep_items(text: str) -> List[str]:
    text = clean_text(text)
    if not text or text == "待补充":
        return []
    items = re.split(r"(?:(?<=\])\s*(?=\[)|(?<=\.)\s+(?=\d+\.)|(?<=。)\s*|(?<=；)\s*|(?<=：)\s*(?=\d+\.))", text)
    results = []
    for item in items:
        item = clean_text(item)
        if len(item) >= 10:
            results.append(item)
    return results[:8] if results else [text]


def parse_year(text: str) -> Optional[int]:
    match = re.search(r"(19|20)\d{2}", text or "")
    return int(match.group(0)) if match else None


def parse_cited(text: str) -> Optional[int]:
    match = re.search(r"(\d+)", text or "")
    return int(match.group(1)) if match else None


def score_scholar_item(item: Dict, target_name: str, name_variants: List[str], direction_keywords: str) -> int:
    score = 0
    meta = item.get("meta", "")
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    if is_relevant_author_text(meta, target_name, name_variants):
        score += 10
    else:
        authors = parse_author_names(meta)
        if any(is_relevant_author_text(author, target_name, name_variants) for author in authors):
            score += 8

    year = item.get("year") or 0
    if year >= CURRENT_YEAR - 1:
        score += 6
    elif year >= CURRENT_YEAR - 3:
        score += 4
    elif year >= CURRENT_YEAR - 5:
        score += 2

    if topic_hit(title, direction_keywords) or topic_hit(snippet, direction_keywords):
        score += 3
    if item.get("cited"):
        score += min(3, int(item["cited"] / 50))
    return score


def dedupe_scholar_items(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for item in items:
        key = normalize_ascii_name(item.get("title", "")) or clean_text(item.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def scholar_search(queries: List[str], target_name: str, name_variants: List[str], direction_keywords: str) -> Dict:
    result = {
        "queries": queries,
        "base": "",
        "profile_name": "",
        "profile_url": "",
        "items": [],
    }

    query_param_sets = [
        {"scisbd": "0"},
        {"scisbd": "1", "as_ylo": str(CURRENT_YEAR - 2)},
    ]

    for base in SCHOLAR_BASES:
        collected = []
        profile_candidates = []
        for query in queries:
            for extra in query_param_sets:
                params = {"q": query}
                params.update(extra)
                try:
                    response = fetch(f"{base}/scholar", params=params)
                except Exception:
                    continue

                soup = BeautifulSoup(response.text, "lxml")
                for node in soup.select(".gs_ri")[:10]:
                    title_node = node.select_one(".gs_rt")
                    meta_node = node.select_one(".gs_a")
                    snippet_node = node.select_one(".gs_rs")
                    cite_node = node.find("a", string=re.compile(r"Cited by|被引用"))
                    link_node = title_node.find("a") if title_node else None
                    title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
                    meta = clean_text(meta_node.get_text(" ", strip=True)) if meta_node else ""
                    snippet = clean_text(snippet_node.get_text(" ", strip=True)) if snippet_node else ""
                    cite = clean_text(cite_node.get_text(" ", strip=True)) if cite_node else ""
                    collected.append({
                        "title": title,
                        "meta": meta,
                        "snippet": snippet,
                        "url": link_node.get("href") if link_node else "",
                        "year": parse_year(meta or title or snippet),
                        "cited": parse_cited(cite),
                    })

                for a in soup.find_all("a", href=re.compile(r"/citations\?user=")):
                    profile_candidates.append({
                        "name": clean_text(a.get_text(" ", strip=True)),
                        "url": base + a.get("href"),
                    })

        collected = dedupe_scholar_items(collected)
        collected.sort(
            key=lambda item: (
                score_scholar_item(item, target_name, name_variants, direction_keywords),
                item.get("year") or 0,
                item.get("cited") or 0,
            ),
            reverse=True,
        )

        if collected:
            result["base"] = base
            result["items"] = collected[:8]
            for candidate in profile_candidates:
                if exact_name_match(target_name, candidate["name"]) or any(
                    exact_name_match(variant, candidate["name"]) for variant in name_variants
                ):
                    result["profile_name"] = candidate["name"]
                    result["profile_url"] = candidate["url"]
                    break
            return result

    return result


def scholar_profile(url: str) -> Dict:
    profile = {
        "name": "",
        "affiliation": "",
        "citations_all": "",
        "citations_recent": "",
        "h_all": "",
        "h_recent": "",
        "i10_all": "",
        "i10_recent": "",
        "top_papers": [],
    }
    if not url:
        return profile

    response = fetch(url)
    soup = BeautifulSoup(response.text, "lxml")
    profile["name"] = clean_text((soup.select_one("#gsc_prf_in") or {}).get_text(" ", strip=True) if soup.select_one("#gsc_prf_in") else "")
    profile["affiliation"] = clean_text((soup.select_one(".gsc_prf_il") or {}).get_text(" ", strip=True) if soup.select_one(".gsc_prf_il") else "")

    stats = [clean_text(td.get_text(" ", strip=True)) for td in soup.select("#gsc_rsb_st td")]
    if len(stats) >= 9:
        profile["citations_all"] = stats[1]
        profile["citations_recent"] = stats[2]
        profile["h_all"] = stats[4]
        profile["h_recent"] = stats[5]
        profile["i10_all"] = stats[7]
        profile["i10_recent"] = stats[8]

    for row in soup.select(".gsc_a_tr")[:8]:
        title = row.select_one(".gsc_a_at")
        year = row.select_one(".gsc_a_y")
        cited = row.select_one(".gsc_a_c")
        profile["top_papers"].append({
            "title": clean_text(title.get_text(" ", strip=True)) if title else "",
            "year": clean_text(year.get_text(" ", strip=True)) if year else "",
            "cited": clean_text(cited.get_text(" ", strip=True)) if cited else "",
        })

    return profile


def extract_homepage_aliases(target_name: str, homepage_text: str) -> List[str]:
    aliases = []
    for variant in build_name_variants(target_name):
        if variant and variant in homepage_text:
            aliases.append(variant)
    return dedupe_keep_order(aliases)


def choose_openalex_queries(target_name: str, scholar_profile_name: str, homepage_text: str) -> List[str]:
    queries = []
    if scholar_profile_name:
        queries.append(scholar_profile_name)
    queries.extend(extract_homepage_aliases(target_name, homepage_text))
    queries.extend(build_name_variants(target_name))
    if not contains_chinese(target_name):
        queries.append(target_name)
    return dedupe_keep_order(queries)


def topic_hit(title: str, keywords_text: str) -> bool:
    haystack = f"{title} {keywords_text}".lower()
    return any(keyword.lower() in haystack for keyword in DOMAIN_KEYWORDS)


def score_openalex_candidate(item: Dict, query: str, target_name: str, name_variants: List[str]) -> int:
    display_name = clean_text(item.get("display_name", ""))
    insts = item.get("last_known_institutions") or []
    institution = " ".join(clean_text(inst.get("display_name", "")) for inst in insts[:2])
    stats = item.get("summary_stats") or {}
    h_index = stats.get("h_index") or 0
    works_count = item.get("works_count") or 0
    cited_by_count = item.get("cited_by_count") or 0

    score = 0
    if contains_bit_institution(institution):
        score += 20
    if exact_name_match(query, display_name):
        score += 8
    if exact_name_match(target_name, display_name):
        score += 6
    if any(exact_name_match(variant, display_name) for variant in name_variants):
        score += 6
    if h_index > 0:
        score += 2
    if works_count >= 10:
        score += 2
    if cited_by_count >= 50:
        score += 1
    return score


def openalex_lookup(queries: List[str], direction_keywords: str, target_name: str, name_variants: List[str]) -> Dict:
    result = {
        "query": "",
        "tried_queries": queries,
        "author_name": "",
        "author_id": "",
        "institution": "",
        "h_index": "",
        "works_count": "",
        "cited_by_count": "",
        "recent_works": [],
        "valid": False,
        "institution_match": False,
        "match_note": "",
    }
    if not queries:
        return result

    best_candidate = None
    best_query = ""
    best_score = -1
    for query in queries:
        try:
            response = fetch("https://api.openalex.org/authors", params={"search": query, "per-page": 10})
        except Exception:
            continue

        for item in response.json().get("results", []):
            score = score_openalex_candidate(item, query, target_name, name_variants)
            if score > best_score:
                best_score = score
                best_candidate = item
                best_query = query

    result["query"] = best_query
    if not best_candidate:
        result["match_note"] = "未找到可用作者候选。"
        return result

    result["author_name"] = clean_text(best_candidate.get("display_name", ""))
    result["author_id"] = best_candidate.get("id", "")
    insts = best_candidate.get("last_known_institutions") or []
    result["institution"] = clean_text(insts[0].get("display_name", "")) if insts else ""
    result["institution_match"] = contains_bit_institution(result["institution"])
    stats = best_candidate.get("summary_stats") or {}
    result["h_index"] = str(stats.get("h_index", "")) if stats.get("h_index") is not None else ""
    result["works_count"] = str(best_candidate.get("works_count", ""))
    result["cited_by_count"] = str(best_candidate.get("cited_by_count", ""))

    if not result["author_id"]:
        result["match_note"] = "作者候选缺少 OpenAlex ID。"
        return result

    try:
        works_resp = fetch(
            "https://api.openalex.org/works",
            params={"filter": f"author.id:{result['author_id']}", "per-page": 8, "sort": "publication_year:desc"},
        )
        works = works_resp.json().get("results", [])
    except Exception:
        works = []

    recent_works = []
    hit_count = 0
    recent_year_count = 0
    for work in works:
        title = clean_text(work.get("display_name", ""))
        year = work.get("publication_year")
        year_text = str(year or "")
        recent_works.append({"title": title, "year": year_text})
        if topic_hit(title, direction_keywords):
            hit_count += 1
        if year and year >= CURRENT_YEAR - 3:
            recent_year_count += 1

    result["recent_works"] = recent_works
    h_index_num = parse_cited(result["h_index"]) or 0
    works_count_num = parse_cited(result["works_count"]) or 0
    cited_by_num = parse_cited(result["cited_by_count"]) or 0
    stats_strong_enough = h_index_num >= 5 or works_count_num >= 10 or cited_by_num >= 100
    works_signal_ok = len(recent_works) >= 2 and (hit_count >= 1 or recent_year_count >= 2)

    if result["institution_match"] and stats_strong_enough and works_signal_ok:
        result["valid"] = True
        result["match_note"] = "作者与北理机构匹配，通过 OpenAlex 校验。"
    elif result["institution_match"] and not stats_strong_enough:
        result["match_note"] = "作者与北理机构匹配，但 OpenAlex 统计量过弱，疑似低质量条目，未纳入正式补充源。"
    elif result["institution_match"]:
        result["match_note"] = "作者与北理机构匹配，但近期 works 领域相关度不足，未纳入正式补充源。"
    elif result["author_name"]:
        result["match_note"] = f"命中作者 {result['author_name']}，但机构为 {result['institution'] or '未知'}，未纳入正式补充源。"
    else:
        result["match_note"] = "OpenAlex 候选不可靠。"
    return result


def extract_recent_homepage_items(rep_items: List[str]) -> List[Dict]:
    items = []
    for item in rep_items:
        year = parse_year(item)
        if year:
            items.append({"title": item, "year": str(year)})
    items.sort(key=lambda item: parse_year(item["year"]) or 0, reverse=True)
    return items[:5]


def compute_freshness(
    scholar_items: List[Dict],
    scholar_profile_papers: List[Dict],
    openalex_recent: List[Dict],
    homepage_recent: List[Dict],
    homepage_pub_date: str,
) -> Tuple[str, str]:
    years = []
    years.extend(item["year"] for item in scholar_items if item.get("year"))
    years.extend(parse_year(item.get("year", "")) for item in scholar_profile_papers if item.get("year"))
    years.extend(parse_year(item.get("year", "")) for item in openalex_recent if item.get("year"))
    years.extend(parse_year(item.get("year", "")) for item in homepage_recent if item.get("year"))
    years = [y for y in years if y]

    latest_year = max(years) if years else parse_year(homepage_pub_date)
    if not latest_year:
        return "低", "缺少近年论文年份信号，主页时效无法确认。"
    if latest_year >= CURRENT_YEAR - 1:
        return "高", f"已识别到 {latest_year} 年论文/活动信号。"
    if latest_year >= CURRENT_YEAR - 3:
        return "中", f"最近可见论文/活动信号为 {latest_year} 年。"
    return "低", f"最近可见论文/活动信号仅到 {latest_year} 年，疑似过时。"


def build_recent_items(scholar: Dict, openalex: Dict, homepage_recent: List[Dict]) -> List[Dict]:
    items = []
    for item in scholar.get("items", []):
        items.append({"title": clean_text(item.get("title", "")), "year": item.get("year") or 0, "source": "scholar"})
    if openalex.get("valid"):
        for item in openalex.get("recent_works", []):
            items.append({"title": clean_text(item.get("title", "")), "year": parse_year(item.get("year", "")) or 0, "source": "openalex"})
    for item in homepage_recent:
        items.append({"title": clean_text(item.get("title", "")), "year": parse_year(item.get("year", "")) or 0, "source": "homepage"})

    seen = set()
    deduped = []
    for item in sorted(items, key=lambda x: x["year"], reverse=True):
        key = normalize_ascii_name(item["title"]) or item["title"]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def infer_primary_themes(row: Dict, directions: List[str], intro: str, recent_items: List[Dict]) -> List[Dict]:
    recent_corpus = " ".join(item["title"] for item in recent_items[:8]).lower()
    direction_corpus = " ".join(directions).lower()
    intro_corpus = intro.lower()
    fallback_corpus = row.get("direction_keywords", "").lower() if not directions else ""

    scores = []
    for bucket in THEME_BUCKETS:
        score = 0
        score += 3 * sum(1 for keyword in bucket["keywords"] if keyword.lower() in recent_corpus)
        score += 2 * sum(1 for keyword in bucket["keywords"] if keyword.lower() in direction_corpus)
        score += 1 * sum(1 for keyword in bucket["keywords"] if keyword.lower() in intro_corpus)
        score += 1 * sum(1 for keyword in bucket["keywords"] if keyword.lower() in fallback_corpus)
        if score > 0:
            scores.append((score, bucket))
    scores.sort(key=lambda x: x[0], reverse=True)
    if scores:
        return [bucket for _, bucket in scores[:2]]

    institute = row.get("research_institute", "")
    if "电动车辆" in institute:
        return [THEME_BUCKETS[0], THEME_BUCKETS[1]]
    if "智能车辆" in institute:
        return [THEME_BUCKETS[2]]
    if "特种车辆" in institute:
        return [THEME_BUCKETS[3], THEME_BUCKETS[4]]
    return []


def infer_recent_focus(recent_items: List[Dict], directions: List[str]) -> str:
    corpus = " ".join(item["title"] for item in recent_items[:6]).lower()
    matches = []
    for bucket in RECENT_TOPIC_BUCKETS:
        score = sum(1 for keyword in bucket["keywords"] if keyword.lower() in corpus)
        if score > 0:
            matches.append((score, bucket["label"]))
    matches.sort(key=lambda x: x[0], reverse=True)
    labels = dedupe_keep_order(label for _, label in matches)
    if labels:
        return "、".join(labels[:3])
    if directions:
        return "、".join(directions[:2])
    if recent_items:
        return "；".join(item["title"] for item in recent_items[:2])
    return "近年重点尚不够清晰，需进入 Layer 3 再抓论文摘要。"


def infer_related_supervisors(row: Dict, rows: List[Dict], evidence_text: str) -> List[Tuple[str, str]]:
    peers = [r["name"] for r in rows if r["name"] != row["name"] and r["research_institute"] == row["research_institute"]]
    evidence_text = clean_text(evidence_text)
    explicit = []
    for peer in peers:
        count = len(re.findall(re.escape(peer), evidence_text))
        if count > 0:
            explicit.append((peer, count))
    explicit.sort(key=lambda x: x[1], reverse=True)

    related = []
    used = set()
    for peer, count in explicit[:4]:
        reason = "近期论文/主页中出现共同署名" if count == 1 else "近期论文/主页中多次共同出现"
        related.append((peer, reason))
        used.add(peer)

    for peer in peers:
        if len(related) >= 4:
            break
        if peer in used:
            continue
        related.append((peer, "同研究所推测，可能共享平台或大方向"))
        used.add(peer)
    return related


def infer_recommendation(
    name: str,
    freshness_level: str,
    completeness: str,
    openalex: Dict,
    scholar_prof: Dict,
    recent_items: List[Dict],
    special_note: str,
) -> Tuple[str, str]:
    score = 0
    if freshness_level == "高":
        score += 2
    elif freshness_level == "中":
        score += 1
    else:
        score -= 2

    if completeness == "高":
        score += 1
    if openalex.get("valid"):
        score += 1
    if recent_items and (recent_items[0].get("year") or 0) >= CURRENT_YEAR - 1:
        score += 1

    scholar_h = parse_cited(scholar_prof.get("h_all", "")) or 0
    if scholar_h >= 40:
        score += 1

    if "院士" in special_note or "高被引" in special_note:
        score += 1
    if "调任" in special_note or "退休" in special_note:
        score -= 3
    if "副院长" in special_note or "行政" in special_note:
        score -= 1

    if score >= 4:
        return "强烈推荐", "近年信号强，科研影响力或平台条件突出，适合作为优先跟进对象。"
    if score >= 2:
        return "推荐", "方向和近年公开信号都不错，值得进入候选池。"
    if score >= 0:
        return "可作为备选", "有一定研究基础，但还需要结合近期论文和招生状态再判断。"
    return "谨慎", "公开信号偏旧或存在岗位/退休/行政等不确定性，不建议直接进入优先名单。"


def build_portrait(
    row: Dict,
    primary_themes: List[Dict],
    freshness_level: str,
    openalex: Dict,
    special_note: str,
    intro: str,
    social: str,
) -> str:
    institute = row.get("research_institute", "")
    theme_text = "、".join(theme["label"] for theme in primary_themes) if primary_themes else row.get("direction_keywords", "相关方向")

    if "院士" in special_note:
        base = "顶层平台型导师"
    elif "主任" in intro or "主任" in social or "所长" in intro or "系主任" in social:
        base = "平台/团队型导师"
    elif openalex.get("valid") and (parse_cited(openalex.get("h_index", "")) or 0) >= 30:
        base = "学术影响力较强的研究型导师"
    elif "特种车辆" in institute:
        base = "硬核工程型导师"
    else:
        base = "稳健的工程研究型导师"

    freshness_part = {
        "高": "近年仍有持续公开论文信号",
        "中": "近年仍能看到一定更新",
        "低": "公开学术信号偏旧，需要进一步核验",
    }[freshness_level]
    return f"整体看属于{base}，主轴在 {theme_text}；{freshness_part}。"


def build_analysis(
    row: Dict,
    rows: List[Dict],
    directions: List[str],
    intro: str,
    social: str,
    scholar: Dict,
    scholar_prof: Dict,
    openalex: Dict,
    homepage_recent: List[Dict],
    completeness: str,
    freshness_level: str,
    special_note: str,
) -> Dict:
    recent_items = build_recent_items(scholar, openalex, homepage_recent)
    primary_themes = infer_primary_themes(row, directions, intro, recent_items)
    recent_focus = infer_recent_focus(recent_items, directions)
    field_assessment = primary_themes[0]["assessment"] if primary_themes else "方向可做，但需要结合近期论文才能判断真正切题的切入点。"
    recommendation, recommendation_reason = infer_recommendation(
        row["name"], freshness_level, completeness, openalex, scholar_prof, recent_items, special_note
    )
    portrait = build_portrait(row, primary_themes, freshness_level, openalex, special_note, intro, social)
    evidence_text = " ".join(
        [intro, social] + [item.get("meta", "") for item in scholar.get("items", [])] + [item.get("title", "") for item in recent_items]
    )
    related = infer_related_supervisors(row, rows, evidence_text)
    return {
        "direction_summary": "、".join(theme["label"] for theme in primary_themes) if primary_themes else "待进一步确认",
        "recent_focus": recent_focus,
        "field_assessment": field_assessment,
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "portrait": portrait,
        "related": related,
    }


def make_profile(candidate: Dict, all_rows: List[Dict], homepage: Dict, scholar: Dict, scholar_prof: Dict, openalex: Dict) -> Tuple[str, Dict]:
    name = candidate["name"]
    institute = candidate["research_institute"]
    title_rank = candidate["title_rank"]
    direction_keywords = candidate.get("direction_keywords", "")

    basic = homepage["basic"]
    sections = homepage["sections"]
    source_ok = homepage["ok"]
    profile_url = candidate["profile_url"]

    position = basic.get("职称", title_rank or "待补充")
    college_major = basic.get("学院专业") or basic.get("学院") or candidate.get("college", "")
    office = basic.get("办公地址", "待补充")
    postcode = basic.get("邮编", "待补充")
    phone = basic.get("办公电话", "待补充")
    email = basic.get("邮箱", "待补充")

    intro = sections.get("简介与研究方向") or sections.get("教育及工作经历") or "待补充"
    homepage_direction_text = sections.get("研究方向") or direction_keywords
    directions = split_directions(homepage_direction_text) or split_directions(direction_keywords)
    rep_items = split_rep_items(sections.get("代表性论文及项目", ""))
    homepage_recent = extract_recent_homepage_items(rep_items)
    honors = sections.get("成果及荣誉", "待补充")
    social = sections.get("社会职务", "待补充")

    freshness_level, freshness_note = compute_freshness(
        scholar["items"],
        scholar_prof.get("top_papers", []),
        openalex["recent_works"] if openalex.get("valid") else [],
        homepage_recent,
        homepage["pub_date"],
    )

    source_parts = []
    if source_ok:
        source_parts.append("北理主页")
    if scholar["items"]:
        source_parts.append("Google Scholar结果页")
    if scholar_prof.get("name"):
        source_parts.append("Google Scholar Profile")
    if openalex.get("valid"):
        source_parts.append("OpenAlex")

    profile_metrics_ok = scholar_prof.get("name") and (
        exact_name_match(name, scholar_prof.get("name", "")) or any(
            exact_name_match(variant, scholar_prof.get("name", "")) for variant in build_name_variants(name)
        )
    )
    completeness_score = 0
    completeness_score += 1 if source_ok else 0
    completeness_score += 1 if scholar["items"] else 0
    completeness_score += 1 if profile_metrics_ok else 0
    completeness_score += 1 if openalex.get("valid") else 0
    completeness = "高" if completeness_score >= 3 else "中" if completeness_score >= 2 else "低"

    special_note = SPECIAL_NOTES.get(name, candidate.get("special_status", ""))
    analysis = build_analysis(
        candidate,
        all_rows,
        directions,
        intro,
        social,
        scholar,
        scholar_prof,
        openalex,
        homepage_recent,
        completeness,
        freshness_level,
        special_note,
    )

    lines = [
        f"# {name} — 学术画像（Layer 2 浅层，多源增强版）",
        "",
        f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d')}",
        "> **画像层级**: Layer 2（多源浅层 / 主页静态信息 + 近期论文信号）",
        f"> **已使用数据源**: {' + '.join(source_parts) if source_parts else '待补充'}",
        "> ⚠️ **重要提示**: 本画像已不再仅依赖高校主页，但仍不是 Layer 3。套磁前仍需抓最近2年论文全量列表与合作者网络。",
        "",
        "## 基本信息",
        "",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| **姓名** | {name} |",
        f"| **职称** | {position} |",
        f"| **学院/专业** | {college_major} |",
        f"| **研究所** | {institute} |",
        f"| **职称等级** | {title_rank} |",
        f"| **办公地址** | {office} |",
        f"| **邮编** | {postcode} |",
        f"| **办公电话** | {phone} |",
        f"| **邮箱** | {email} |",
        f"| **主页链接** | {profile_url} |",
        "",
        "## 研判总结",
        "",
        f"- **研究方向归纳**: {analysis['direction_summary']}",
        f"- **最近关注**: {analysis['recent_focus']}",
        f"- **这个方向好不好做**: {analysis['field_assessment']}",
        f"- **是否推荐**: {analysis['recommendation']}。{analysis['recommendation_reason']}",
        f"- **综合科研画像**: {analysis['portrait']}",
        "",
        "## 主页静态信息",
        "",
        intro,
        "",
        "## 主页标注研究方向",
        "",
    ]

    if directions:
        for idx, item in enumerate(directions, 1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("- 待补充")

    lines.extend([
        "",
        "## Google Scholar 近期论文信号",
        "",
    ])
    if scholar["items"]:
        for item in scholar["items"][:5]:
            year = item.get("year") or "年份待补充"
            lines.append(f"- `{year}` {item.get('title', '待补充')} | {item.get('meta', '待补充')}")
    else:
        lines.append("- 未稳定获取到 Scholar 结果页论文信号")

    lines.extend([
        "",
        "## Google Scholar 指标",
        "",
    ])
    if profile_metrics_ok:
        lines.extend([
            f"- **Profile 名称**: {scholar_prof.get('name', '待补充')}",
            f"- **机构**: {scholar_prof.get('affiliation', '待补充')}",
            f"- **总引用**: {scholar_prof.get('citations_all', '待补充')}",
            f"- **近年引用**: {scholar_prof.get('citations_recent', '待补充')}",
            f"- **h-index**: {scholar_prof.get('h_all', '待补充')}",
            f"- **近年 h-index**: {scholar_prof.get('h_recent', '待补充')}",
        ])
    else:
        lines.append("- Scholar profile 未命中可靠作者，当前仅保留结果页论文信号。")

    lines.extend([
        "",
        "## OpenAlex 补充信号",
        "",
    ])
    if openalex.get("valid"):
        lines.extend([
            f"- **作者**: {openalex.get('author_name', '待补充')}",
            f"- **机构**: {openalex.get('institution', '待补充')}",
            f"- **h-index**: {openalex.get('h_index', '待补充')}",
            f"- **works_count**: {openalex.get('works_count', '待补充')}",
            f"- **cited_by_count**: {openalex.get('cited_by_count', '待补充')}",
        ])
        for item in openalex.get("recent_works", [])[:3]:
            lines.append(f"- `{item.get('year', '')}` {item.get('title', '')}")
    elif openalex.get("query"):
        lines.append(f"- {openalex.get('match_note', 'OpenAlex 候选不可靠，未纳入正式补充源。')}")
    else:
        lines.append("- 当前未使用 OpenAlex 补充。")

    lines.extend([
        "",
        "## 主页代表作 / 项目",
        "",
    ])
    if rep_items:
        for item in rep_items[:5]:
            lines.append(f"- {item}")
    else:
        lines.append("- 待补充")

    lines.extend([
        "",
        "## 成果及荣誉",
        "",
        honors,
        "",
        "## 社会职务",
        "",
        social,
        "",
        "## Layer 2 判断",
        "",
        "- **Layer 1 评级**: A",
        f"- **信息完整度**: {completeness}",
        f"- **信息新鲜度**: {freshness_level}",
        f"- **新鲜度说明**: {freshness_note}",
        f"- **是否建议进入 Layer 3**: {'建议' if freshness_level in {'高', '中'} else '谨慎'}",
    ])

    if special_note:
        lines.extend(["", "## 特殊注意点", "", f"- {special_note}"])

    lines.extend(["", "## 可能同组 / 强合作老师", ""])
    if analysis["related"]:
        for peer, reason in analysis["related"]:
            lines.append(f"- **{peer}**: {reason}")
    else:
        lines.append("- 暂未识别到明确同组线索，建议后续结合近年论文共同作者再核验。")

    lines.extend([
        "",
        "---",
        "",
        "> **源说明**: 当前 Layer 2 已采用多源交叉，不再仅依赖主页。Scholar 是主学术源，OpenAlex 只在作者与机构同时可靠时补充。",
        "> **Layer 2 局限**: 尚未抓近2年全量论文、合作者网络、项目公告、主页更新时间链。",
        "> **下一步**: 真正准备联系的导师，应进入 Layer 3（近2年论文全抓 + 新合作者 + 项目动态 + 招生活跃度核验）。",
    ])

    return "\n".join(lines), analysis


def build_scholar_queries(row: Dict) -> List[str]:
    name = row["name"]
    keyword = clean_text((row.get("direction_keywords") or "").split(";")[0])
    queries = []
    if contains_chinese(name):
        queries.append(f'author:"{name}" 北京理工大学')
        queries.append(f'"{name}" 北京理工大学 {keyword}'.strip())
    else:
        queries.append(f'{name} Beijing Institute of Technology')
        if keyword:
            queries.append(f'"{name}" Beijing Institute of Technology {keyword}')
    return dedupe_keep_order(queries)


def main():
    parser = argparse.ArgumentParser(description="Layer 2 批量画像生成（多源增强版）")
    parser.add_argument("--input", required=True, help="A档候选 CSV")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    args = parser.parse_args()

    rows = read_candidates(args.input)
    os.makedirs(args.output_dir, exist_ok=True)

    report_lines = [
        "# Layer 2 批量生成报告（多源增强版）",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**输入文件**: `{args.input}`",
        f"**候选人数**: {len(rows)}",
        "",
        "| 姓名 | 主页 | Scholar | Scholar Profile | OpenAlex | 输出文件 |",
        "|------|------|---------|-----------------|----------|----------|",
    ]

    done = 0
    for row in rows:
        homepage = {"ok": False, "basic": {}, "sections": {}, "pub_date": "", "text": ""}
        try:
            homepage_resp = fetch(row["profile_url"])
            homepage_soup = BeautifulSoup(homepage_resp.text, "lxml")
            basic, sections, pub_date, page_text = extract_homepage_tables(homepage_soup)
            homepage = {"ok": True, "basic": basic, "sections": sections, "pub_date": pub_date, "text": page_text}
        except Exception:
            pass

        name_variants = build_name_variants(row["name"])
        scholar = scholar_search(
            build_scholar_queries(row),
            row["name"],
            name_variants,
            row.get("direction_keywords", ""),
        )

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

        openalex = {}
        openalex_queries = choose_openalex_queries(row["name"], scholar_prof.get("name", ""), homepage.get("text", ""))
        try:
            openalex = openalex_lookup(openalex_queries, row.get("direction_keywords", ""), row["name"], name_variants)
        except Exception:
            openalex = {"query": openalex_queries[0] if openalex_queries else "", "valid": False, "recent_works": [], "match_note": "OpenAlex 查询失败。"}

        profile_text, analysis = make_profile(row, rows, homepage, scholar, scholar_prof, openalex)
        output_path = os.path.join(args.output_dir, f'{row["name"]}_profile.md')
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(profile_text)

        report_lines.append(
            f'| {row["name"]} | {"✅" if homepage["ok"] else "⚠️"} | '
            f'{"✅" if scholar.get("items") else "⚠️"} | '
            f'{"✅" if scholar_prof.get("name") else "⚠️"} | '
            f'{"✅" if openalex.get("valid") else "⚠️"} | `{os.path.basename(output_path)}` |'
        )
        done += 1
        time.sleep(1.2)

    report_lines.extend(["", f"**完成数量**: {done}"])
    report_path = os.path.join(args.output_dir, "BATCH_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"[完成] 生成 {done} 份 Layer 2 多源画像 -> {args.output_dir}")
    print(f"[报告] {report_path}")


if __name__ == "__main__":
    main()
