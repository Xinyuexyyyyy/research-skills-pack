#!/usr/bin/env python3
"""
Supervisor Scout — Layer 3 论文了解文件
=====================================
基于 Layer 3 深度画像和近期核心论文，为每位老师生成真正可用的
“了解文件”：讲清最近在做什么、代表论文解决什么问题、以及这对套磁意味着什么。
"""

import argparse
import csv
import html
import os
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from layer2_batch_profiles import HEADERS, THEME_BUCKETS, clean_text, contains_chinese, normalize_ascii_name
from layer3_overview_report import Layer3Row, attach_scores, parse_row


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
REQUEST_PAUSE_SEC = 0.3

DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)
TITLE_HINT_KEYWORDS = [
    "方法", "研究", "控制", "规划", "估计", "优化", "展望", "综述", "特性", "设计",
    "prediction", "planner", "planning", "control", "optimization", "estimation",
    "trajectory", "adaptive", "fault", "stability", "vibration", "comfort",
]
PRESTIGE_VENUE_KEYWORDS = [
    "ieee transactions",
    "ieee journal",
    "transactions on",
    "mechanical systems and signal processing",
    "nonlinear dynamics",
    "international journal of mechanical sciences",
    "applied thermal engineering",
    "chinese journal of mechanical engineering",
    "vehicular technology",
    "industrial electronics",
    "transportation electrification",
    "intelligent vehicles",
    "sensors journal",
]
JOURNAL_SIGNAL_KEYWORDS = [
    "journal",
    "transactions",
    "letters",
    "proceedings",
    "engineering",
    "vehicle",
    "vehicles",
    "mechanical",
    "dynamics",
    "electronics",
    "control",
]
LOW_SIGNAL_VENUES = [
    "北京理工大学 学报",
    "journal.bit.edu.cn",
]


@dataclass
class PaperEntry:
    year: int
    raw_title: str
    venue: str
    cited: int
    authors: List[str]
    doi: str = ""
    clean_title: str = ""


@dataclass
class PaperMetadata:
    title: str
    doi: str
    year: int
    venue: str
    abstract: str
    url: str
    authors: List[str]
    citation_count: int
    source: str
    confidence: str


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", clean_text(name))


def read_csv(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_section_bullets(title: str, text: str) -> List[str]:
    match = re.search(rf"## {re.escape(title)}\s+(.*?)(?=\n## |\Z)", text, re.S)
    if not match:
        return []
    out = []
    for line in match.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
    return out


def extract_doi(text: str) -> str:
    match = DOI_RE.search(text or "")
    return match.group(1) if match else ""


def clean_title_candidate(raw_title: str) -> str:
    title = clean_text(raw_title)
    title = DOI_RE.sub("", title)
    title = re.sub(r"\(SCI.*?\)|\(EI.*?\)|Outstanding Technical Paper\.?", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" ,.;；。")

    if not title:
        return ""

    comma_parts = [clean_text(part) for part in re.split(r"[，,;；]", title) if clean_text(part)]
    candidates = []
    for part in comma_parts:
        lowered = part.lower()
        if len(part) < 6:
            continue
        if any(keyword.lower() in lowered for keyword in TITLE_HINT_KEYWORDS):
            candidates.append(part)
    if candidates:
        candidates.sort(key=len, reverse=True)
        return candidates[0].strip(" .")

    return title


def parse_paper_entries(profile_path: Path) -> List[PaperEntry]:
    text = profile_path.read_text(encoding="utf-8")
    entries = []
    for bullet in parse_section_bullets("近 2 年论文", text):
        year_match = re.match(r"`(\d{4})`\s*(.+)", bullet)
        if not year_match:
            continue
        year = int(year_match.group(1))
        body = year_match.group(2)
        parts = [clean_text(part) for part in body.split(" | ")]
        raw_title = parts[0] if parts else ""
        venue = parts[1] if len(parts) > 1 else ""
        cited = 0
        authors: List[str] = []
        for part in parts[2:]:
            cited_match = re.search(r"引用\s*(\d+)", part)
            if cited_match:
                cited = int(cited_match.group(1))
            if "作者:" in part:
                authors = [clean_text(a) for a in re.split(r"[，,;；]", part.split("作者:", 1)[1]) if clean_text(a) and clean_text(a) != "作者待补充"]

        doi = extract_doi(body)
        clean_title = clean_title_candidate(raw_title)
        entries.append(PaperEntry(
            year=year,
            raw_title=raw_title,
            venue=venue,
            cited=cited,
            authors=authors,
            doi=doi,
            clean_title=clean_title or raw_title,
        ))
    return entries


def title_similarity(a: str, b: str) -> float:
    a_norm = normalize_ascii_name(a) or re.sub(r"\s+", "", clean_text(a)).lower()
    b_norm = normalize_ascii_name(b) or re.sub(r"\s+", "", clean_text(b)).lower()
    if not a_norm or not b_norm:
        return 0.0
    if contains_chinese(a) or contains_chinese(b):
        if a_norm in b_norm or b_norm in a_norm:
            return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def strip_jats(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")
    return clean_text(soup.get_text(" ", strip=True))


def request_json(url: str, params: Optional[Dict] = None) -> Dict:
    response = requests.get(url, headers=HEADERS, timeout=25, params=params)
    response.raise_for_status()
    return response.json()


def search_crossref_title(title: str) -> PaperMetadata:
    fallback = PaperMetadata(title=title, doi="", year=0, venue="", abstract="", url="", authors=[], citation_count=0, source="title-only", confidence="低")
    try:
        payload = request_json("https://api.crossref.org/works", params={"query.title": title, "rows": 5})
    except Exception:
        return fallback

    best_item = None
    best_score = 0.0
    for item in payload.get("message", {}).get("items", []):
        item_title = clean_text((item.get("title") or [""])[0])
        score = title_similarity(title, item_title)
        if score > best_score:
            best_score = score
            best_item = item

    if not best_item or best_score < 0.55:
        return fallback

    year = 0
    for key in ["published-print", "published-online", "issued"]:
        date_parts = best_item.get(key, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            year = int(date_parts[0][0])
            break

    authors = []
    for author in best_item.get("author", [])[:8]:
        given = clean_text(author.get("given", ""))
        family = clean_text(author.get("family", ""))
        full = clean_text(f"{given} {family}")
        if full:
            authors.append(full)

    return PaperMetadata(
        title=clean_text((best_item.get("title") or [title])[0]) or title,
        doi=clean_text(best_item.get("DOI", "")),
        year=year,
        venue=clean_text((best_item.get("container-title") or [""])[0]),
        abstract=strip_jats(best_item.get("abstract", "")),
        url=clean_text(best_item.get("URL", "")),
        authors=authors,
        citation_count=0,
        source="crossref-title",
        confidence="中" if best_score >= 0.72 else "低",
    )


def fetch_crossref_doi(doi: str) -> PaperMetadata:
    fallback = PaperMetadata(title="", doi=doi, year=0, venue="", abstract="", url="", authors=[], citation_count=0, source="crossref-doi", confidence="低")
    if not doi:
        return fallback
    try:
        payload = request_json(f"https://api.crossref.org/works/{doi}")
    except Exception:
        return fallback

    item = payload.get("message", {})
    year = 0
    for key in ["published-print", "published-online", "issued"]:
        date_parts = item.get(key, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            year = int(date_parts[0][0])
            break

    authors = []
    for author in item.get("author", [])[:8]:
        full = clean_text(f"{author.get('given', '')} {author.get('family', '')}")
        if full:
            authors.append(full)

    return PaperMetadata(
        title=clean_text((item.get("title") or [""])[0]),
        doi=clean_text(item.get("DOI", "")) or doi,
        year=year,
        venue=clean_text((item.get("container-title") or [""])[0]),
        abstract=strip_jats(item.get("abstract", "")),
        url=clean_text(item.get("URL", "")),
        authors=authors,
        citation_count=0,
        source="crossref-doi",
        confidence="高",
    )


def fetch_semantic_scholar_doi(doi: str) -> PaperMetadata:
    fallback = PaperMetadata(title="", doi=doi, year=0, venue="", abstract="", url="", authors=[], citation_count=0, source="semantic-doi", confidence="低")
    if not doi:
        return fallback
    try:
        payload = request_json(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "title,year,abstract,authors,venue,citationCount,url,externalIds"},
        )
    except Exception:
        return fallback

    authors = [clean_text(author.get("name", "")) for author in payload.get("authors", [])[:8] if clean_text(author.get("name", ""))]
    return PaperMetadata(
        title=clean_text(payload.get("title", "")),
        doi=clean_text((payload.get("externalIds") or {}).get("DOI", "")) or doi,
        year=int(payload.get("year") or 0),
        venue=clean_text(payload.get("venue", "")),
        abstract=clean_text(payload.get("abstract", "")),
        url=clean_text(payload.get("url", "")),
        authors=authors,
        citation_count=int(payload.get("citationCount") or 0),
        source="semantic-doi",
        confidence="高",
    )


def merge_metadata(entry: PaperEntry, crossref_title: PaperMetadata, crossref_doi: PaperMetadata, semantic_doi: PaperMetadata) -> PaperMetadata:
    title = semantic_doi.title or crossref_doi.title or crossref_title.title or entry.clean_title
    doi = semantic_doi.doi or crossref_doi.doi or crossref_title.doi or entry.doi
    year = entry.year or semantic_doi.year or crossref_doi.year or crossref_title.year
    venue = semantic_doi.venue or crossref_doi.venue or crossref_title.venue or entry.venue
    abstract = semantic_doi.abstract or crossref_doi.abstract or crossref_title.abstract
    url = semantic_doi.url or crossref_doi.url or crossref_title.url
    authors = entry.authors or semantic_doi.authors or crossref_doi.authors or crossref_title.authors
    citation_count = semantic_doi.citation_count or entry.cited
    confidence = "高" if abstract and doi else "中" if doi or abstract else "低"
    source_parts = [meta.source for meta in [crossref_title, crossref_doi, semantic_doi] if meta and (meta.title or meta.abstract or meta.doi)]
    return PaperMetadata(
        title=title,
        doi=doi,
        year=year,
        venue=venue,
        abstract=abstract,
        url=url,
        authors=authors,
        citation_count=citation_count,
        source=" + ".join(source_parts) or "title-only",
        confidence=confidence,
    )


def venue_tier(meta: PaperMetadata, entry: PaperEntry) -> Tuple[int, str]:
    venue_text = clean_text(meta.venue or entry.venue).lower()
    if any(keyword in venue_text for keyword in PRESTIGE_VENUE_KEYWORDS):
        return 3, "近年 SCI/IEEE"
    if meta.doi and meta.abstract and any(keyword in venue_text for keyword in JOURNAL_SIGNAL_KEYWORDS):
        return 2, "近年 DOI 期刊/会议"
    if meta.doi:
        return 1, "有 DOI，需回源核刊"
    if any(keyword.lower() in venue_text for keyword in LOW_SIGNAL_VENUES):
        return 0, "校内学报题目级"
    return 0, "题目级"


def score_metadata(meta: PaperMetadata, entry: PaperEntry) -> Tuple[int, int, int]:
    confidence_score = {"高": 3, "中": 2, "低": 0}.get(meta.confidence, 0)
    abstract_score = 2 if meta.abstract else 0
    doi_score = 1 if meta.doi else 0
    venue_score, _ = venue_tier(meta, entry)
    return (confidence_score + abstract_score + doi_score + venue_score, meta.year or entry.year, entry.cited)


def infer_topic_label(title: str, abstract: str, recent_focus: str) -> str:
    corpus = f"{title} {abstract} {recent_focus}".lower()
    best_label = recent_focus or "待补"
    best_score = -1
    for bucket in THEME_BUCKETS:
        score = sum(1 for keyword in bucket["keywords"] if keyword.lower() in corpus)
        if score > best_score:
            best_score = score
            best_label = bucket["label"]
    return best_label


def get_bucket_detail(label: str) -> Dict:
    for bucket in THEME_BUCKETS:
        if bucket["label"] == label:
            return bucket
    return {"label": label, "assessment": "待补", "keywords": []}


def summarize_problem_method(title: str, abstract: str) -> Tuple[str, str]:
    corpus = f"{title} {abstract}".lower()
    if "review" in corpus or "综述" in corpus or "展望" in corpus:
        return (
            "这篇更像方向综述/路线盘点，适合先拿来理解老师最近在关注哪些问题簇、哪些技术路线已经被作者分层。",
            "精读时重点抓作者怎样划分现有方法、哪里被认为是瓶颈、未来方向落在算法、平台还是系统集成。",
        )
    if any(keyword in corpus for keyword in ["trajectory", "path", "planning", "planner", "轨迹", "路径", "规划"]):
        return (
            "这篇核心大概率是围绕复杂场景下的轨迹规划或轨迹预测，重点不在单一感知模块，而在场景约束和决策/规划闭环。",
            "精读时先看问题场景定义、状态/约束建模、损失函数或优化目标，以及和 baseline 的对比方式。",
        )
    if any(keyword in corpus for keyword in ["control", "mpc", "predictive", "adaptive", "fault", "控制", "预测", "自适应"]):
        return (
            "这篇更偏控制与系统方法，重点通常是控制对象建模、控制器结构和稳定性/性能保证。",
            "精读时先看系统模型、控制器结构、约束处理、稳定性证明，以及仿真/实车验证是否足够硬。",
        )
    if any(keyword in corpus for keyword in ["battery", "电池", "soh", "soc", "degradation", "热管理"]):
        return (
            "这篇大概率围绕电池状态估计、安全或寿命机理，适合从数据、模型和验证场景三个层次拆解。",
            "精读时优先看状态变量定义、数据来源、估计框架以及泛化到不同工况/老化阶段的能力。",
        )
    if any(keyword in corpus for keyword in ["motor", "pmsm", "current", "电机", "永磁同步"]):
        return (
            "这篇更偏电驱/电机控制，通常会把电机模型、观测器结构和扰动抑制放在一起讨论。",
            "精读时重点看控制回路怎么设计、扰动从哪里来、实验平台是否足够接近真实工况。",
        )
    if any(keyword in corpus for keyword in ["vibration", "nvh", "ride comfort", "振动", "舒适", "稳定性"]):
        return (
            "这篇更偏车辆动力学、振动控制或舒适性/稳定性权衡，适合看模型和控制目标的折中。",
            "精读时先看动力学模型、激励源、评价指标，以及舒适性和稳定性是否被同时优化。",
        )
    return (
        "这篇论文至少能帮助确认老师近期真正押注的问题，不建议只看标题后就泛泛写兴趣。",
        "精读时先抓研究对象、方法主线和验证方式，再判断它和你背景能否形成具体连接。",
    )


def field_sentence(topic_label: str) -> str:
    bucket = get_bucket_detail(topic_label)
    return bucket.get("assessment", "待补")


def infer_solution_sentence(title: str, abstract: str) -> str:
    corpus = f"{title} {abstract}".lower()
    if "review" in corpus or "综述" in corpus or "展望" in corpus:
        return "作者不是单做一个小算法，而是在梳理这个方向已经有哪些技术路线、各自卡在哪、下一步应该往哪里推。"
    if any(keyword in corpus for keyword in ["trajectory", "path", "planning", "planner", "轨迹", "路径", "规划"]):
        return "作者的核心思路通常是把复杂场景里的轨迹/路径问题形式化，再用学习或优化框架把“能走”“走得稳”“走得好”同时兼顾。"
    if any(keyword in corpus for keyword in ["prediction", "估计", "kalman", "state estimation", "trajectory prediction"]):
        return "作者的核心思路是先把关键状态表示清楚，再用估计器或学习框架去提升在复杂工况下的鲁棒性和实时性。"
    if any(keyword in corpus for keyword in ["control", "mpc", "adaptive", "fault", "控制", "预测控制"]):
        return "作者的核心思路是围绕控制对象建模，再叠加控制器结构、约束处理和性能保证，证明方法在复杂条件下仍然可用。"
    if any(keyword in corpus for keyword in ["battery", "电池", "degradation", "soh", "soc", "热管理"]):
        return "作者的核心思路一般是把电池内部状态、外部工况和安全/寿命指标联起来，用模型或估计方法做更稳的判断。"
    if any(keyword in corpus for keyword in ["motor", "pmsm", "电机", "电流控制", "观测器"]):
        return "作者的核心思路更偏电机控制与观测器设计，重点是把模型误差、扰动和控制精度同时压住。"
    if any(keyword in corpus for keyword in ["vibration", "nvh", "ride comfort", "振动", "舒适", "稳定性"]):
        return "作者的核心思路是把动力学建模和多目标控制放在一起，处理稳定性、舒适性和复杂地形适应之间的权衡。"
    return "作者的核心思路需要回到引言和方法部分再确认，但至少可以先看清楚问题定义、方法主线和验证方式。"


def title_based_problem(title: str) -> str:
    title_l = title.lower()
    if "kalman" in title_l or "状态估计" in title or "estimation" in title_l:
        return "作者在解决复杂车辆或多模态平台运行时状态不好估、模式切换后估计不稳的问题。"
    if "永磁同步电机" in title or "pmsm" in title_l:
        if "扰动抑制" in title or "disturbance" in title_l:
            return "作者在解决永磁同步电机电流控制容易受扰动和模型误差影响，导致控制精度下降的问题。"
        if "转矩脉动" in title or "torque ripple" in title_l:
            return "作者在解决开绕组永磁同步电机运行时转矩脉动影响性能和稳定性的问题。"
    if "通流特性" in title or "油道" in title:
        return "作者在解决高速行星传动机构内部润滑/流动过程不好描述、进而影响传动性能判断的问题。"
    if "研究现状与展望" in title or "overview" in title_l or "综述" in title or "展望" in title:
        return "作者在梳理这个方向已经发展到哪一步、关键瓶颈卡在哪里、下一步还能怎么推进。"
    if any(k in title_l for k in ["trajectory", "path", "planning", "planner"]) or any(k in title for k in ["轨迹", "路径", "规划"]):
        return "作者在解决复杂场景下车辆轨迹规划或预测既要可行、又要稳、还要适应真实工况的问题。"
    if any(k in title_l for k in ["vibration", "ride comfort"]) or any(k in title for k in ["振动", "舒适", "稳定性"]):
        return "作者在解决车辆稳定性、舒适性和复杂工况适应之间难以同时兼顾的问题。"
    if "degradation mechanism" in title_l or "state of health" in title_l or "健康状态" in title:
        return "作者在梳理动力电池劣化机理和健康状态估计这条线里，哪些问题已经相对清楚，哪些还没有统一答案。"
    return "作者在处理一个比主页方向标签更具体的技术问题，只看方向词已经不足以代表论文内容。"


def title_based_solution(title: str) -> str:
    title_l = title.lower()
    if "kalman" in title_l or "状态估计" in title or "estimation" in title_l:
        return "从标题看，作者用了双 Kalman/状态估计框架，重点是让多模态车辆在复杂工况下的状态估计更稳。"
    if "永磁同步电机" in title or "pmsm" in title_l:
        if "双观测器" in title or "observer" in title_l:
            return "从标题看，作者把双观测器和无差拍预测电流控制绑在一起，目标是更快、更稳地抑制扰动。"
        return "从标题看，作者通过控制策略设计去压低电机转矩脉动，而不是只做结构层修补。"
    if "通流特性" in title or "油道" in title:
        return "从标题看，作者围绕油道内部流动建模和特性分析展开，想把传动系统里一个偏隐蔽但关键的机理问题说清楚。"
    if "研究现状与展望" in title or "overview" in title_l or "综述" in title or "展望" in title:
        return "从标题看，作者不是在推一个单点算法，而是在把该方向路线、问题和发展趋势系统化整理。"
    if any(k in title_l for k in ["trajectory", "path", "planning", "planner"]) or any(k in title for k in ["轨迹", "路径", "规划"]):
        return "从标题看，作者是在用规划/预测框架处理复杂场景约束，而不是只做静态几何路径。"
    if any(k in title_l for k in ["vibration", "ride comfort"]) or any(k in title for k in ["振动", "舒适", "稳定性"]):
        return "从标题看，作者把稳定性、舒适性和车辆控制放进一个联合框架，而不是各做一半。"
    if "degradation mechanism" in title_l or "state of health" in title_l:
        return "从标题看，作者在用综述式方式把电池劣化机理和 SOH 估计两块放到同一个知识框架里。"
    return "从标题看，作者在给一个更具体的问题定义和解决路线，而不只是重复大方向。"


def title_based_method(title: str) -> str:
    title_l = title.lower()
    if "kalman" in title_l or "状态估计" in title or "estimation" in title_l:
        return "精读时优先确认状态量怎么定义、模式切换怎么处理、双滤波/双估计器到底各自负责什么。"
    if "永磁同步电机" in title or "pmsm" in title_l:
        return "精读时优先看电机模型、观测器结构、扰动定义和实验平台，不要只看控制框图。"
    if "通流特性" in title or "油道" in title:
        return "精读时优先看流动模型、边界条件、仿真/试验验证，以及这些分析怎么真正回到传动系统性能。"
    if "研究现状与展望" in title or "overview" in title_l or "综述" in title or "展望" in title:
        return "精读时优先看作者怎么分技术路线、怎么定义瓶颈，以及他把未来机会押在算法、平台还是系统集成。"
    if any(k in title_l for k in ["trajectory", "path", "planning", "planner"]) or any(k in title for k in ["轨迹", "路径", "规划"]):
        return "精读时优先看场景设定、约束建模、优化目标和基线对比，确认它到底解决了哪类复杂工况。"
    if any(k in title_l for k in ["vibration", "ride comfort"]) or any(k in title for k in ["振动", "舒适", "稳定性"]):
        return "精读时优先看动力学模型、多目标指标以及稳定性和舒适性是怎么被同时优化的。"
    if "degradation mechanism" in title_l or "state of health" in title_l:
        return "精读时优先看作者如何划分劣化机理、SOH 估计方法谱系，以及哪些路线被判断为更有前景。"
    return "精读时先抓问题对象、方法主线和验证方式，别只盯标题里的大词。"


def title_based_result(title: str) -> str:
    title_l = title.lower()
    if "研究现状与展望" in title or "overview" in title_l or "综述" in title or "展望" in title:
        return "这类论文的价值通常不在单一实验数字，而在它把方向地图重新整理清楚，帮你判断老师到底押注哪条技术线。"
    if "kalman" in title_l or "状态估计" in title or "estimation" in title_l:
        return "从标题可判断，作者至少在强调状态估计精度、鲁棒性或多模态场景下的稳定性提升。"
    if "永磁同步电机" in title or "pmsm" in title_l:
        return "从标题可判断，作者至少在强调电机控制精度、动态响应或转矩品质的改进。"
    if "通流特性" in title or "油道" in title:
        return "从标题可判断，这篇至少会给出传动机构内部流动/润滑特性的定性或定量结论。"
    if any(k in title_l for k in ["trajectory", "path", "planning", "planner"]) or any(k in title for k in ["轨迹", "路径", "规划"]):
        return "从标题可判断，这篇至少是在证明新的规划/预测框架比现有做法更适配复杂工况。"
    if any(k in title_l for k in ["vibration", "ride comfort"]) or any(k in title for k in ["振动", "舒适", "稳定性"]):
        return "从标题可判断，这篇至少试图同时改善稳定性和舒适性，而不是只优化一个指标。"
    if "degradation mechanism" in title_l or "state of health" in title_l:
        return "从标题可判断，这篇至少在给出电池劣化机理与 SOH 估计方法之间的系统性对应关系。"
    return "当前摘要没拿到，但标题已经足够说明作者在推进一个具体而不是泛泛的技术问题。"


def infer_core_contribution(title: str, abstract: str) -> List[str]:
    corpus = f"{title} {abstract}".lower()
    items = []
    if not abstract:
        return [
            title_based_solution(title),
            "这篇至少能帮你确认老师最近真正研究的对象和问题，而不是只确认一个大方向标签。",
        ]
    if any(keyword in corpus for keyword in ["review", "综述", "展望"]):
        items.append("把一个分散的技术方向系统化地分层整理出来，而不是只报告单一实验结果。")
    if any(keyword in corpus for keyword in ["trajectory", "path", "planning", "planner", "轨迹", "路径", "规划"]):
        items.append("把规划/预测问题和复杂场景约束真正绑在一起，而不是只做理想场景下的算法演示。")
    if any(keyword in corpus for keyword in ["control", "mpc", "adaptive", "fault", "控制"]):
        items.append("给出可落到系统层的控制框架，而不只是停留在静态建模。")
    if any(keyword in corpus for keyword in ["battery", "电池", "degradation", "soh", "soc"]):
        items.append("把状态估计、安全或寿命问题和真实工况联系起来，强调模型/数据的工程可用性。")
    if any(keyword in corpus for keyword in ["motor", "pmsm", "电机", "观测器"]):
        items.append("把电机控制中的扰动、观测和动态响应作为一个整体来处理。")
    if any(keyword in corpus for keyword in ["vibration", "nvh", "ride comfort", "振动", "舒适"]):
        items.append("把动力学性能和舒适性/稳定性这样的多目标约束一起优化。")
    if not items:
        items.append("至少说明老师最近不是停留在旧方向标签，而是在持续推进一个更具体的问题链条。")
    return items[:3]


def infer_result_sentence(title: str, abstract: str) -> str:
    text = clean_text(abstract)
    if not text:
        return title_based_result(title)
    sentences = re.split(r"(?<=[。.!?])\s+", text)
    keywords = ["outperform", "improve", "demonstrate", "show", "achieve", "reduce", "enhance", "prove", "结果", "提升", "降低", "优于"]
    for sentence in sentences:
        s = clean_text(sentence)
        if any(keyword in s.lower() for keyword in keywords):
            return s
    return abstract_key_takeaway(text, title)


def infer_suspicious_detail(meta: PaperMetadata, entry: PaperEntry) -> str:
    if not meta.abstract:
        return "摘要没稳定抓到，当前最缺的是问题设置和实验验证的硬信息；邮件里可以引用问题和方法方向，但不要引用具体效果结论。"
    if "review" in (meta.title or "").lower() or "综述" in meta.title or "展望" in meta.title:
        return "综述文适合帮你建立方向地图，但不适合作为唯一套磁切口，因为它不直接代表组里的具体技术实现。"
    if meta.confidence == "低":
        return "这篇元数据可信度偏低，最好回到原文主页或 PDF 核对作者、刊物和 DOI。"
    if meta.citation_count == 0 and (meta.year or entry.year) >= 2025:
        return "论文很新，暂时看不到引用和后续反馈，别把标题上的漂亮措辞直接当成熟结论。"
    return "要重点核对实验对象、基线是否公平，以及作者是不是把仿真结果写得过于理想化。"


def infer_teacher_understanding(row: Layer3Row, metas: List[PaperMetadata]) -> Tuple[str, str]:
    titles = "；".join(meta.title for meta in metas[:2] if meta.title)
    if any("review" in (meta.title or "").lower() or "综述" in meta.title or "展望" in meta.title for meta in metas):
        summary = f"{row.name} 最近主线落在 {row.recent_focus}，公开信号里既有方向梳理，也有具体技术问题。"
    elif any(any(k in (meta.title + meta.abstract).lower() for k in ["trajectory", "planning", "planner", "prediction", "path"]) for meta in metas):
        summary = f"{row.name} 近两年的公开工作集中在 {row.recent_focus}，重点偏向复杂场景下的规划、预测和系统闭环。"
    elif any(any(k in (meta.title + meta.abstract).lower() for k in ["control", "adaptive", "mpc", "vibration", "电机", "观测器"]) for meta in metas):
        summary = f"{row.name} 最近更偏机理和控制，关注的是把控制性能、约束处理和实际工况一起做实。"
    else:
        summary = f"{row.name} 最近公开论文不算多，但在 {row.recent_focus} 上仍能看到连续推进。"

    implication = (
        f"联系 {row.name} 时，邮件主线应直接落到 {titles or '最近代表论文'} 里的具体问题、方法或实验对象。"
    )
    return summary, implication


def format_authors(meta: PaperMetadata, entry: PaperEntry) -> str:
    return "，".join(meta.authors[:6] or entry.authors[:6]) or "作者待补"


def build_fast_overview(meta: PaperMetadata, entry: PaperEntry, topic_label: str) -> List[str]:
    title = meta.title or entry.clean_title
    abstract = meta.abstract
    field_text = field_sentence(topic_label)
    if abstract:
        problem_note, read_focus = summarize_problem_method(title, abstract)
        solution = infer_solution_sentence(title, abstract)
        result = infer_result_sentence(title, abstract)
    else:
        problem_note = title_based_problem(title)
        read_focus = title_based_method(title)
        solution = title_based_solution(title)
        result = title_based_result(title)
    return [
        "### 论文速览（大白话版）",
        "",
        f"#### 1. 研究领域：这篇论文属于什么方向？",
        f"这篇属于 `{topic_label}`，更具体地说，是在处理和 `{topic_label}` 相关的一个近期具体问题。{field_text}",
        "",
        f"#### 2. 技术问题：为什么要做这件事？",
        problem_note,
        "",
        f"#### 3. 解决方案：作者提出了什么核心思路？",
        solution,
        "",
        f"#### 4. 研究方法：作者大概怎么做的？",
        read_focus,
        "",
        f"#### 5. 核心结论：作者主要发现了什么？",
        result,
        "",
    ]


def build_5c(meta: PaperMetadata, topic_label: str) -> List[str]:
    clarity = "高" if meta.abstract else "中"
    context = "中" if meta.doi else "低"
    correctness = "中" if meta.abstract else "低"
    contributions = "；".join(infer_core_contribution(meta.title, meta.abstract))
    return [
        "### 5C 评估",
        "",
        "| 问题 | 答案 | 置信度 |",
        "|---|---|---|",
        f"| **Category** — 哪类论文？ | {topic_label} 方向的近期代表作 | 中 |",
        f"| **Context** — 与哪些工作相关？ | 和老师最近 2 年在 `{topic_label}` 上的连续工作直接相关 | {context} |",
        f"| **Correctness** — 核心假设合理吗？ | 当前只能做摘要级判断，核心实验仍需回原文核对 | {correctness} |",
        f"| **Contributions** — 主要贡献 | {contributions} | 中 |",
        f"| **Clarity** — 写得清楚吗？ | {'摘要和元数据足够支撑速读' if meta.abstract else '标题清楚，但需要回原文补方法和结果细节'} | {clarity} |",
        "",
    ]


def build_second_pass(meta: PaperMetadata, entry: PaperEntry, topic_label: str) -> List[str]:
    title = meta.title or entry.clean_title
    abstract = meta.abstract
    terms = []
    corpus = f"{title} {abstract}".lower()
    if any(k in corpus for k in ["trajectory", "path", "planning", "planner"]):
        terms.extend([("trajectory planning", "给车生成一条既能走、又安全、又满足车辆约束的运动轨迹"), ("prediction", "先判断周围交通参与者接下来可能怎么动")])
    if any(k in corpus for k in ["mpc", "predictive control"]):
        terms.append(("MPC", "一种提前往前看几步、再决定当前怎么控的控制方法"))
    if any(k in corpus for k in ["kalman", "state estimation"]):
        terms.append(("Kalman filter", "一种根据噪声观测不断修正系统状态估计的方法"))
    if any(k in corpus for k in ["vibration", "ride comfort", "nvh"]):
        terms.append(("NVH", "噪声、振动与声振舒适性问题的统称"))
    if any(k in corpus for k in ["pmsm", "motor", "current"]):
        terms.append(("PMSM", "永磁同步电机，是新能源车常见的驱动电机类型"))
    if not terms and ("永磁同步电机" in title or "PMSM" in title):
        terms.append(("PMSM", "永磁同步电机，是新能源车常见的驱动电机类型"))
    if not terms:
        terms.append(("核心术语", "需要回原文标题、引言和方法部分确认，当前摘要信息不够完整"))

    lines = [
        "### 精读抓手",
        "",
        "#### 术语表",
        "",
        "| 术语 | 人话解释 |",
        "|---|---|",
    ]
    for term, explanation in terms[:5]:
        lines.append(f"| {term} | {explanation} |")
    lines.extend([
        "",
        "#### 方法论：作者大概是怎么做的？",
        "",
        f"- **准备问题场景**: 先把 `{topic_label}` 里最麻烦的工况定义清楚，决定研究对象和评价指标。",
        f"- **搭方法主线**: {title_based_solution(title) if not abstract else f'再围绕 `{title}` 暗示的方法主线去建模、估计或控制，而不是只做经验调参。'}",
        f"- **给出验证**: 最后通过仿真、实验、对比基线或案例分析证明这条方法线比现有做法更稳或更准。",
        "",
        "#### 我现在最该盯的点",
        "",
        f"- {title_based_method(title) if not abstract else summarize_problem_method(title, abstract)[1]}",
        f"- {infer_suspicious_detail(meta, entry)}",
        "",
    ])
    return lines


def build_third_pass(meta: PaperMetadata, entry: PaperEntry, topic_label: str) -> List[str]:
    lines = [
        "### 深读提醒",
        "",
        "#### 这篇论文没说清楚什么",
        "",
        f"- **最该追问的假设**: 这篇在 `{topic_label}` 上默认了什么工况、什么数据、什么控制边界？这些边界一旦变掉，结论还站不站得住？",
        f"- **我最担心的薄弱点**: {infer_suspicious_detail(meta, entry)}",
        f"- **如果你要基于它继续做**: 第一件事不是照搬方法，而是先确认实验对象、评价指标和 baseline 是否真的适用于你的背景。",
        "",
    ]
    return lines


def abstract_key_takeaway(abstract: str, title: str) -> str:
    text = clean_text(abstract)
    if not text:
        return title_based_result(title)
    sentences = re.split(r"(?<=[。.!?])\s+", text)
    picked = []
    for sentence in sentences:
        sentence = clean_text(sentence)
        if len(sentence) < 20:
            continue
        picked.append(sentence)
        if len(picked) >= 2:
            break
    return " ".join(picked) if picked else text[:220]


def build_email_angle(row: Layer3Row, meta: PaperMetadata) -> str:
    corpus = f"{meta.title} {meta.abstract} {row.recent_focus}".lower()
    if any(keyword in corpus for keyword in ["trajectory", "planning", "路径", "轨迹", "规划"]):
        return "邮件里可以从复杂场景下的规划-控制闭环、约束建模或多车环境决策切入。"
    if any(keyword in corpus for keyword in ["control", "mpc", "adaptive", "控制", "预测"]):
        return "邮件里可以落到模型驱动控制、约束处理或稳定性保证这些具体问题。"
    if any(keyword in corpus for keyword in ["battery", "电池", "能量管理", "hybrid", "电机", "永磁同步"]):
        return "邮件里可以从能量管理、电驱控制或状态估计切入，说明你愿意把模型、控制和验证连起来。"
    if any(keyword in corpus for keyword in ["vibration", "nvh", "振动", "舒适"]):
        return "邮件里可以抓车辆动力学、振动控制和多目标权衡这条线。"
    return "邮件里直接点论文里的问题设置、方法主线或实验对象。"


def strongest_evidence_label(enriched: List[Tuple[PaperEntry, PaperMetadata]]) -> str:
    if not enriched:
        return "暂无可靠论文信号"
    best_level = max(venue_tier(meta, entry)[0] for entry, meta in enriched)
    if best_level >= 3:
        return "近年 SCI/IEEE"
    if best_level >= 2:
        return "近年 DOI 期刊/会议"
    if best_level >= 1:
        return "仅有 DOI 线索"
    return "仅有题目级信号"


def concise_takeaway(title: str, abstract: str) -> str:
    corpus = f"{title} {abstract}".lower()
    if any(keyword in corpus for keyword in ["trajectory", "path", "planning", "planner", "轨迹", "路径", "规划"]):
        return "核心是复杂场景下的轨迹规划或预测，重点看约束建模、优化目标和闭环验证。"
    if any(keyword in corpus for keyword in ["control", "mpc", "adaptive", "fault", "控制", "预测控制"]):
        return "核心是控制对象建模和控制器设计，重点看稳定性、约束处理和实验验证。"
    if any(keyword in corpus for keyword in ["battery", "电池", "degradation", "soh", "soc", "热管理"]):
        return "核心是电池状态估计、安全或寿命问题，重点看数据来源、状态变量和泛化能力。"
    if any(keyword in corpus for keyword in ["motor", "pmsm", "电机", "电流控制", "观测器"]):
        return "核心是电驱或电机控制，重点看模型误差、扰动抑制和控制精度。"
    if any(keyword in corpus for keyword in ["vibration", "nvh", "ride comfort", "振动", "舒适", "稳定性"]):
        return "核心是车辆动力学和多目标控制，重点看稳定性、舒适性和复杂工况适应。"
    if "review" in corpus or "综述" in corpus or "展望" in corpus:
        return "核心是把路线、瓶颈和未来方向梳理清楚，适合拿来判断老师真正押注的方向。"
    return "核心要回到原文引言和方法部分确认，当前只能先锁定研究对象和问题定义。"


def evidence_risk(meta: PaperMetadata, entry: PaperEntry) -> str:
    detail = infer_suspicious_detail(meta, entry)
    detail = detail.replace("当前只能做摘要级判断，核心实验仍需回原文核对。", "核心实验仍需回原文核对。")
    return detail


def top_titles(enriched: List[Tuple[PaperEntry, PaperMetadata]], limit: int = 2) -> str:
    return "；".join(meta.title or entry.clean_title for entry, meta in enriched[:limit]) if enriched else "待补"


def paper_card(row: Layer3Row, entry: PaperEntry, meta: PaperMetadata, index: int) -> List[str]:
    quality_score, quality_label = venue_tier(meta, entry)
    title = meta.title or entry.clean_title
    source = f"{meta.year or entry.year} / {meta.venue or entry.venue or '待补'}"
    if quality_score >= 3 and meta.doi:
        ref_line = f"{quality_label}，DOI {meta.doi}"
    elif meta.doi:
        ref_line = f"{quality_label}，DOI {meta.doi}"
    else:
        ref_line = quality_label
    return [
        f"## 核心论文 {index}",
        "",
        f"- **标题**: {title}",
        f"- **来源**: {source}",
        f"- **引用等级**: {ref_line}",
        f"- **作者**: {format_authors(meta, entry)}",
        f"- **你该抓的点**: {concise_takeaway(title, meta.abstract)}",
        f"- **这篇对邮件最有用的地方**: {build_email_angle(row, meta)}",
        f"- **当前风险**: {evidence_risk(meta, entry)}",
        "",
    ]


def choose_target_papers(row: Layer3Row, profile_path: Path, max_papers: int = 3) -> List[PaperEntry]:
    entries = parse_paper_entries(profile_path)
    if not entries:
        return []
    entries.sort(key=lambda item: (item.year, item.cited, len(item.clean_title)), reverse=True)
    return entries[: max(max_papers + 2, 5)]


def enrich_paper(entry: PaperEntry) -> PaperMetadata:
    crossref_title = search_crossref_title(entry.clean_title)
    time.sleep(REQUEST_PAUSE_SEC)
    doi = entry.doi or crossref_title.doi
    crossref_doi = fetch_crossref_doi(doi)
    time.sleep(REQUEST_PAUSE_SEC)
    semantic_doi = fetch_semantic_scholar_doi(doi)
    time.sleep(REQUEST_PAUSE_SEC)
    return merge_metadata(entry, crossref_title, crossref_doi, semantic_doi)


def write_teacher_brief(row: Layer3Row, profile_path: Path, output_dir: Path) -> Dict:
    papers = choose_target_papers(row, profile_path)
    enriched = [(entry, enrich_paper(entry)) for entry in papers]
    enriched.sort(key=lambda pair: score_metadata(pair[1], pair[0]), reverse=True)
    enriched = enriched[:2]
    if enriched and venue_tier(enriched[0][1], enriched[0][0])[0] <= 0:
        enriched = enriched[:1]
    metas_only = [meta for _, meta in enriched]
    strongest_topic = row.recent_focus
    teacher_summary, teacher_implication = infer_teacher_understanding(row, metas_only)
    evidence_label = strongest_evidence_label(enriched)
    recommended_titles = top_titles(enriched)
    lines = [
        f"# {row.name} — 论文了解文件",
        "",
        f"> **研究所**: {row.research_institute}",
        f"> **当前层级判断**: {row.judgement}",
        f"> **推荐读文批次**: {row.read_batch}",
        f"> **核心主题**: {strongest_topic}",
        "",
        "## 一眼结论",
        "",
        f"- **最近在做什么**: {teacher_summary}",
        f"- **对套磁最有用的判断**: {teacher_implication}",
        f"- **证据硬度**: {evidence_label}",
        f"- **最稳引用论文**: {recommended_titles}",
        f"- **当前最大卡点**: {row.next_action}",
        "",
    ]

    for idx, (entry, meta) in enumerate(enriched, start=1):
        lines.extend(paper_card(row, entry, meta, idx))

    if enriched:
        send_hint = "可以先发" if evidence_label == "近年 SCI/IEEE" and row.read_batch == "第一批" else "补一处后发" if evidence_label in {"近年 SCI/IEEE", "近年 DOI 期刊/会议"} and row.read_batch in {"第一批", "第二批"} else "先缓发"
        lines.extend([
            "## 最后判断",
            "",
            f"- **现在建议**: {send_hint}",
            f"- **最稳邮件主线**: 把邮件落在 {row.recent_focus} 上，再用上面最稳的 1 篇论文作具体切口。",
            f"- **还没补上的硬信息**: {row.next_action}",
            "",
        ])

    output_path = output_dir / f"{safe_filename(row.name)}_understanding.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "name": row.name,
        "paper_count": len(enriched),
        "top_titles": [meta.title or entry.clean_title for entry, meta in enriched],
        "evidence_label": evidence_label,
        "output_path": str(output_path),
    }


def write_overview(rows: List[Layer3Row], outputs: List[Dict], output_dir: Path) -> None:
    by_name = {item["name"]: item for item in outputs}
    send_now = []
    send_later = []
    hold = []
    for row in rows:
        evidence_label = by_name.get(row.name, {}).get("evidence_label", "")
        if evidence_label == "近年 SCI/IEEE" and row.read_batch == "第一批":
            send_now.append(row.name)
        elif evidence_label in {"近年 SCI/IEEE", "近年 DOI 期刊/会议"} and row.read_batch in {"第一批", "第二批"}:
            send_later.append(row.name)
        else:
            hold.append(row.name)
    lines = [
        "# BIT 车辆 A档 Layer 3 论文了解总文件",
        "",
        "## 总结论",
        "",
        f"这一版只保留 7 位老师最近两年的核心论文、证据硬度和发信判断。现在可优先推进的是 {'、'.join(send_now) or '暂无'}；补一处后再发的是 {'、'.join(send_later) or '暂无'}；建议先缓发的是 {'、'.join(hold) or '暂无'}。",
        "",
        "| 顺序 | 姓名 | 建议 | 证据硬度 | 最稳引用论文 | 了解文件 |",
        "|------|------|------|----------|--------------|----------|",
    ]
    for idx, row in enumerate(rows, start=1):
        output = by_name.get(row.name, {})
        file_path = Path(output.get("output_path", ""))
        link = f"[{file_path.name}]({file_path.resolve()})" if file_path else "待补"
        evidence_label = output.get("evidence_label", "待补")
        if evidence_label == "近年 SCI/IEEE" and row.read_batch == "第一批":
            decision = "先发"
        elif evidence_label in {"近年 SCI/IEEE", "近年 DOI 期刊/会议"} and row.read_batch in {"第一批", "第二批"}:
            decision = "补一处后发"
        else:
            decision = "先缓发"
        title_text = "；".join(output.get("top_titles", [])[:1]) or "待补"
        lines.append(
            f"| {idx} | {row.name} | {decision} | {evidence_label} | {title_text} | {link} |"
        )
    lines.extend([
        "",
        "## 你现在最该看什么",
        "",
        "- 先看每位老师的 `证据硬度` 和 `最稳引用论文`，这两项决定邮件能不能站住。",
        "- 再看单人文档里的 `你该抓的点` 和 `这篇对邮件最有用的地方`，它们就是邮件切口。",
        "- 如果文档里只有 `题目级` 或 `校内学报题目级`，当前就不建议硬发。",
    ])
    (output_dir / "LAYER3_UNDERSTANDING_MASTER.md").write_text("\n".join(lines), encoding="utf-8")

    with (output_dir / "LAYER3_UNDERSTANDING_MASTER.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "read_batch", "judgement", "recent_focus", "paper_count", "evidence_label", "understanding_path"])
        writer.writeheader()
        for row in rows:
            output = by_name.get(row.name, {})
            writer.writerow({
                "name": row.name,
                "read_batch": row.read_batch,
                "judgement": row.judgement,
                "recent_focus": row.recent_focus,
                "paper_count": output.get("paper_count", 0),
                "evidence_label": output.get("evidence_label", ""),
                "understanding_path": output.get("output_path", ""),
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 3 套磁前读文版")
    parser.add_argument("--profiles-dir", required=True, help="Layer 3 深度画像目录")
    parser.add_argument("--output-dir", required=True, help="读文版输出目录")
    parser.add_argument("--overview-csv", help="Layer 3 总览 CSV，默认从 profiles-dir 读取")
    args = parser.parse_args()

    profiles_dir = Path(args.profiles_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    overview_csv = Path(args.overview_csv) if args.overview_csv else profiles_dir / "LAYER3_OVERVIEW.csv"
    ordered_names = [row["name"] for row in read_csv(overview_csv)] if overview_csv.exists() else []
    profile_map = {path.stem.replace("_deep", ""): path for path in profiles_dir.glob("*_deep.md")}
    rows = attach_scores([parse_row(profile_map[name]) for name in ordered_names if name in profile_map]) if ordered_names else attach_scores([parse_row(path) for path in profile_map.values()])

    outputs = []
    for row in rows:
        outputs.append(write_teacher_brief(row, profile_map[row.name], output_dir))
        print(f"[保存] {row.name} -> {outputs[-1]['output_path']}")

    write_overview(rows, outputs, output_dir)
    print(f"[完成] 已生成 {len(outputs)} 位老师的读文版")


if __name__ == "__main__":
    main()
