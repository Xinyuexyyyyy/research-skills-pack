#!/usr/bin/env python3
"""
evidence_extractor.py — Batch Pass 1 / Pass 2 extraction for paper-reading.

Reads `pass1_inputs.jsonl`, calls an OpenAI-compatible chat endpoint or a local
mock backend, and writes:
  - pass1_results.json
  - pass2_results.json

Design goals:
  - stdlib-only
  - compatible with both legacy `reading/` and newer `02-reading/` run layouts
  - outputs exactly the JSON arrays expected by `scripts/collect.py`

Examples:
  python3 tools/evidence_extractor.py runs/2026-05-13_thermal_runaway_early_warning --backend mock
  python3 tools/evidence_extractor.py runs/2026-05-13_thermal_runaway_early_warning --model gpt-4.1-mini
  python3 tools/evidence_extractor.py runs/2026-05-13_thermal_runaway_early_warning --stage pass2 --resume
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "paper-reading" / "scripts"))
from common import resolve_run_layout  # noqa: E402


PASS1_CATEGORIES = {
    "review",
    "empirical_cfd",
    "empirical_material",
    "empirical_optimization",
    "empirical_ai",
    "theoretical",
    "survey",
}
PASS1_CORRECTNESS = {"valid", "questionable", "insufficient_info"}
PASS1_CLARITY = {"well_written", "acceptable", "poorly_written"}
PASS1_VERDICTS = {"proceed_to_pass2", "demote_to_qualitative_only", "skip"}
PASS1_CONFIDENCE = {"high", "medium", "low"}

PASS2_CONFIDENCE = {"high", "medium", "low"}
PASS2_SOURCES = {"abstract", "abstract+methods", "fulltext", "title_only"}

PLACEHOLDER_PATTERNS = [
    "available online only",
    "subscription required",
    "abstract not available",
    "abstract unavailable",
]

PASS1_SYSTEM_PROMPT = """你是学术论文分析助手,严格遵循 Keshav Pass 1。

只从输入文本抽取,不要外推,不要编造。字段无信息就写空字符串或空数组。
输出必须是单个 JSON object,并且必须包含:
paper_uid, category, context, correctness_flag, contributions, clarity_score,
pass1_verdict, pass1_confidence, pass1_reason
"""

PASS2_SYSTEM_PROMPT = """你是学术论文证据抽取助手。

只从输入文本抽取,不要外推,不要编造。字段无信息就写空字符串。
输出必须是单个 JSON object,并且必须包含:
paper_uid, population, intervention, comparator, outcome, method,
key_finding_1, key_finding_2, key_finding_3, extraction_confidence,
extraction_source
"""


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(description="Batch evidence extraction for paper-reading")
    parser.add_argument("run_dir", help="Run directory")
    parser.add_argument(
        "--stage",
        choices=("both", "pass1", "pass2"),
        default="both",
        help="Which extraction stages to run",
    )
    parser.add_argument(
        "--backend",
        choices=("openai", "mock"),
        default="openai",
        help="LLM backend; mock is useful for local dry-run validation",
    )
    parser.add_argument("--model", default=os.getenv("EVIDENCE_EXTRACTOR_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N pass1 inputs")
    parser.add_argument("--resume", action="store_true", help="Skip items already present in output JSON")
    parser.add_argument("--timeout", type=int, default=90, help="HTTP timeout seconds")
    parser.add_argument("--retries", type=int, default=3, help="Retries per item")
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Delay between API calls")
    return parser.parse_args(argv[1:])


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_json_array(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def write_json_array(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")


def extract_json_object(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("empty model response")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object found in model response")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model response JSON is not an object")
    return parsed


def is_placeholder_abstract(text: str) -> bool:
    if not text:
        return True
    lowered = text.strip().lower()
    if len(lowered) < 50:
        return True
    return any(pattern in lowered for pattern in PLACEHOLDER_PATTERNS)


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def choose_sentences(text: str, patterns: list[str], limit: int = 3) -> list[str]:
    sentences = split_sentences(text)
    hits = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(pattern in lowered for pattern in patterns):
            hits.append(sentence)
        if len(hits) >= limit:
            break
    if hits:
        return hits
    return sentences[:limit]


def normalize_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(normalize_text(item) for item in value if normalize_text(item))
    return str(value).strip()


def normalize_contributions(value) -> list[str]:
    if isinstance(value, list):
        items = [normalize_text(item) for item in value]
    elif value:
        text = normalize_text(value)
        items = [piece.strip(" -") for piece in re.split(r";|\n", text) if piece.strip()]
    else:
        items = []
    cleaned = [item for item in items if item][:3]
    return cleaned


def infer_category(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    if any(token in text for token in ("review", "state-of-the-art", "comprehensive review")):
        return "review"
    if "survey" in text:
        return "survey"
    if any(token in text for token in ("machine learning", "neural", "cnn", "physics-informed", "data-driven")):
        return "empirical_ai"
    if any(token in text for token in ("optimiz", "multi-objective", "genetic", "pso", "kriging")):
        return "empirical_optimization"
    if any(token in text for token in ("phase change", "pcm", "material", "composite", "thermal conductivity")):
        return "empirical_material"
    if any(token in text for token in ("theorem", "proof", "analytical", "theoretical")):
        return "theoretical"
    return "empirical_cfd"


def mock_pass1(record: dict) -> dict:
    title = normalize_text(record.get("title"))
    abstract = normalize_text(record.get("abstract"))
    keywords = normalize_text(record.get("keywords"))
    category = infer_category(title, abstract)
    contributions = normalize_contributions(
        choose_sentences(
            abstract,
            ["propose", "present", "introduce", "develop", "investigate", "show", "demonstrate", "review"],
        )
    )

    if is_placeholder_abstract(abstract):
        verdict = "skip"
        confidence = "low"
        correctness = "insufficient_info"
        clarity = "poorly_written"
        reason = "abstract 缺失或信息量过低,无法完成 Pass 1"
    elif category in {"review", "survey"}:
        verdict = "demote_to_qualitative_only"
        confidence = "high"
        correctness = "valid"
        clarity = "well_written" if len(split_sentences(abstract)) >= 3 else "acceptable"
        reason = "综述/调查类论文,适合作为定性输入而非 PICO 主证据"
    else:
        method_markers = ("experiment", "simulation", "model", "numerical", "optimiz", "cfd", "fem")
        outcome_markers = re.search(r"\d", abstract) is not None
        has_method = any(marker in abstract.lower() for marker in method_markers)
        verdict = "proceed_to_pass2" if contributions else "skip"
        confidence = "high" if has_method and outcome_markers else "medium"
        correctness = "valid" if has_method else "insufficient_info"
        clarity = "well_written" if len(split_sentences(abstract)) >= 3 else "acceptable"
        reason = "abstract 提供了可抽取的方法和结果线索" if verdict == "proceed_to_pass2" else "贡献信息不足"

    context_parts = [part for part in [title, keywords] if part]
    context = " | ".join(context_parts)[:240]
    return {
        "paper_uid": normalize_text(record.get("paper_uid")),
        "category": category,
        "context": context,
        "correctness_flag": correctness,
        "contributions": contributions or [title[:120]] if title else [],
        "clarity_score": clarity,
        "pass1_verdict": verdict,
        "pass1_confidence": confidence,
        "pass1_reason": reason,
    }


def default_source(record: dict) -> str:
    channel = normalize_text(record.get("channel")).lower()
    if channel == "arxiv":
        return "fulltext"
    if channel == "pending":
        return "title_only"
    return "abstract"


def mock_pass2(record: dict, pass1_result: dict) -> dict:
    title = normalize_text(record.get("title"))
    abstract = normalize_text(record.get("abstract"))
    sentences = split_sentences(abstract)

    intervention = ""
    for sentence in choose_sentences(
        abstract,
        ["propose", "introduce", "develop", "optimiz", "design", "framework", "method", "system"],
        limit=2,
    ):
        if sentence:
            intervention = sentence
            break

    method = ""
    for sentence in choose_sentences(
        abstract,
        ["experiment", "simulation", "numerical", "model", "cfd", "fem", "dataset", "evaluate", "optimization"],
        limit=2,
    ):
        if sentence:
            method = sentence
            break

    outcome = ""
    for sentence in sentences:
        if re.search(r"\d", sentence) or any(token in sentence.lower() for token in ("improv", "reduc", "increase", "decrease")):
            outcome = sentence
            break

    population = sentences[0] if sentences else title
    comparator = ""
    for sentence in sentences:
        lowered = sentence.lower()
        if any(token in lowered for token in ("compared to", "compared with", "versus", " vs ", "baseline")):
            comparator = sentence
            break

    findings = choose_sentences(
        abstract,
        ["result", "show", "demonstrate", "improv", "reduc", "increase", "decrease", "effective"],
        limit=3,
    )
    findings = findings + [""] * (3 - len(findings))

    source = default_source(record)
    if population and intervention and method and outcome:
        confidence = "high" if re.search(r"\d", outcome) else "medium"
    elif population and intervention and method:
        confidence = "medium"
    else:
        confidence = "low"

    if pass1_result.get("pass1_confidence") == "low" and confidence == "high":
        confidence = "medium"

    return {
        "paper_uid": normalize_text(record.get("paper_uid")),
        "population": population[:240],
        "intervention": intervention[:240],
        "comparator": comparator[:240],
        "outcome": outcome[:240],
        "method": method[:240],
        "key_finding_1": findings[0][:240],
        "key_finding_2": findings[1][:240],
        "key_finding_3": findings[2][:240],
        "extraction_confidence": confidence,
        "extraction_source": source,
    }


def render_pass1_prompt(record: dict) -> str:
    payload = {
        "paper_uid": record.get("paper_uid", ""),
        "title": record.get("title", ""),
        "authors": record.get("authors", ""),
        "year": record.get("year", ""),
        "venue": record.get("venue", ""),
        "doi": record.get("doi", ""),
        "abstract": record.get("abstract", ""),
        "keywords": record.get("keywords", ""),
        "channel": record.get("channel", ""),
        "category_candidates": record.get("category_candidates", []),
        "verdict_candidates": record.get("verdict_candidates", []),
    }
    return (
        "请基于以下论文记录完成 Keshav Pass 1,并返回严格 JSON object。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def render_pass2_prompt(record: dict, pass1_result: dict) -> str:
    payload = {
        "paper_uid": record.get("paper_uid", ""),
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "keywords": record.get("keywords", ""),
        "channel": record.get("channel", ""),
        "pass1": {
            "category": pass1_result.get("category", ""),
            "context": pass1_result.get("context", ""),
            "contributions": pass1_result.get("contributions", []),
            "pass1_verdict": pass1_result.get("pass1_verdict", ""),
            "pass1_confidence": pass1_result.get("pass1_confidence", ""),
        },
    }
    return (
        "请基于以下论文记录完成 Pass 2 证据抽取,并返回严格 JSON object。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


class OpenAIChatClient:
    def __init__(self, model: str, api_key: str, base_url: str, timeout: int):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for --backend openai")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = json.load(response)

        choices = raw.get("choices") or []
        if not choices:
            raise ValueError("no choices returned from API")
        content = ((choices[0].get("message") or {}).get("content")) or ""
        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
        return extract_json_object(content)


def sanitize_pass1(result: dict, record: dict) -> dict:
    category = normalize_text(result.get("category"))
    if category not in PASS1_CATEGORIES:
        category = infer_category(normalize_text(record.get("title")), normalize_text(record.get("abstract")))

    correctness = normalize_text(result.get("correctness_flag"))
    if correctness not in PASS1_CORRECTNESS:
        correctness = "insufficient_info"

    clarity = normalize_text(result.get("clarity_score"))
    if clarity not in PASS1_CLARITY:
        clarity = "acceptable"

    verdict = normalize_text(result.get("pass1_verdict"))
    if verdict not in PASS1_VERDICTS:
        verdict = "skip" if is_placeholder_abstract(normalize_text(record.get("abstract"))) else "proceed_to_pass2"

    confidence = normalize_text(result.get("pass1_confidence"))
    if confidence not in PASS1_CONFIDENCE:
        confidence = "medium"

    contributions = normalize_contributions(result.get("contributions"))
    if verdict == "proceed_to_pass2" and not contributions:
        contributions = normalize_contributions(mock_pass1(record).get("contributions"))
    if verdict == "skip":
        confidence = "low"

    return {
        "paper_uid": normalize_text(record.get("paper_uid")),
        "category": category,
        "context": normalize_text(result.get("context"))[:400],
        "correctness_flag": correctness,
        "contributions": contributions,
        "clarity_score": clarity,
        "pass1_verdict": verdict,
        "pass1_confidence": confidence,
        "pass1_reason": normalize_text(result.get("pass1_reason"))[:400],
    }


def sanitize_pass2(result: dict, record: dict, pass1_result: dict) -> dict:
    cleaned = {
        "paper_uid": normalize_text(record.get("paper_uid")),
        "population": normalize_text(result.get("population"))[:400],
        "intervention": normalize_text(result.get("intervention"))[:400],
        "comparator": normalize_text(result.get("comparator"))[:400],
        "outcome": normalize_text(result.get("outcome"))[:400],
        "method": normalize_text(result.get("method"))[:400],
        "key_finding_1": normalize_text(result.get("key_finding_1"))[:400],
        "key_finding_2": normalize_text(result.get("key_finding_2"))[:400],
        "key_finding_3": normalize_text(result.get("key_finding_3"))[:400],
        "extraction_confidence": normalize_text(result.get("extraction_confidence")),
        "extraction_source": normalize_text(result.get("extraction_source")),
    }

    if cleaned["extraction_confidence"] not in PASS2_CONFIDENCE:
        cleaned["extraction_confidence"] = "medium"
    if cleaned["extraction_source"] not in PASS2_SOURCES:
        cleaned["extraction_source"] = default_source(record)

    needs_low = any(not cleaned[field] for field in ("population", "intervention", "method"))
    if needs_low:
        cleaned["extraction_confidence"] = "low"

    if pass1_result.get("pass1_confidence") == "low" and cleaned["extraction_confidence"] == "high":
        cleaned["extraction_confidence"] = "medium"

    return cleaned


def call_with_retry(client, system_prompt: str, user_prompt: str, retries: int, sleep_seconds: float):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return client.complete_json(system_prompt, user_prompt)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(max(1.0, sleep_seconds) * attempt)
    raise last_error


def process_pass1(records: list[dict], args, out_path: Path) -> list[dict]:
    existing = load_json_array(out_path) if args.resume else []
    existing_by_uid = {row.get("paper_uid"): row for row in existing if row.get("paper_uid")}
    results = list(existing_by_uid.values())

    client = None
    if args.backend == "openai":
        client = OpenAIChatClient(args.model, args.api_key, args.base_url, args.timeout)

    total = len(records)
    for index, record in enumerate(records, 1):
        paper_uid = normalize_text(record.get("paper_uid"))
        if paper_uid in existing_by_uid:
            print(f"[pass1 {index}/{total}] skip existing {paper_uid}")
            continue

        if args.backend == "mock":
            raw = mock_pass1(record)
        else:
            raw = call_with_retry(
                client,
                PASS1_SYSTEM_PROMPT,
                render_pass1_prompt(record),
                args.retries,
                args.sleep_seconds,
            )
        cleaned = sanitize_pass1(raw, record)
        results.append(cleaned)
        existing_by_uid[paper_uid] = cleaned
        write_json_array(out_path, sorted(results, key=lambda row: row.get("paper_uid", "")))
        print(f"[pass1 {index}/{total}] done {paper_uid} -> {cleaned['pass1_verdict']} ({cleaned['pass1_confidence']})")
        time.sleep(args.sleep_seconds)

    return sorted(results, key=lambda row: row.get("paper_uid", ""))


def process_pass2(records: list[dict], pass1_results: list[dict], args, out_path: Path) -> list[dict]:
    pass1_by_uid = {row.get("paper_uid"): row for row in pass1_results if row.get("paper_uid")}
    eligible = [
        record for record in records
        if pass1_by_uid.get(record.get("paper_uid"), {}).get("pass1_verdict") == "proceed_to_pass2"
    ]

    existing = load_json_array(out_path) if args.resume else []
    existing_by_uid = {row.get("paper_uid"): row for row in existing if row.get("paper_uid")}
    results = list(existing_by_uid.values())

    client = None
    if args.backend == "openai":
        client = OpenAIChatClient(args.model, args.api_key, args.base_url, args.timeout)

    total = len(eligible)
    for index, record in enumerate(eligible, 1):
        paper_uid = normalize_text(record.get("paper_uid"))
        if paper_uid in existing_by_uid:
            print(f"[pass2 {index}/{total}] skip existing {paper_uid}")
            continue

        pass1_result = pass1_by_uid[paper_uid]
        if args.backend == "mock":
            raw = mock_pass2(record, pass1_result)
        else:
            raw = call_with_retry(
                client,
                PASS2_SYSTEM_PROMPT,
                render_pass2_prompt(record, pass1_result),
                args.retries,
                args.sleep_seconds,
            )
        cleaned = sanitize_pass2(raw, record, pass1_result)
        results.append(cleaned)
        existing_by_uid[paper_uid] = cleaned
        write_json_array(out_path, sorted(results, key=lambda row: row.get("paper_uid", "")))
        print(f"[pass2 {index}/{total}] done {paper_uid} -> {cleaned['extraction_confidence']}")
        time.sleep(args.sleep_seconds)

    return sorted(results, key=lambda row: row.get("paper_uid", ""))


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"ERROR: run_dir not found: {run_dir}", file=sys.stderr)
        return 1

    layout = resolve_run_layout(run_dir)
    reading_dir = layout["reading_dir"]
    reading_dir.mkdir(exist_ok=True)

    pass1_inputs_path = reading_dir / "pass1_inputs.jsonl"
    pass1_output_path = reading_dir / "pass1_results.json"
    pass2_output_path = reading_dir / "pass2_results.json"

    if not pass1_inputs_path.exists():
        print(f"ERROR: missing pass1 inputs: {pass1_inputs_path}", file=sys.stderr)
        return 1

    records = load_jsonl(pass1_inputs_path)
    if args.limit > 0:
        records = records[:args.limit]
    print(f"Inputs: {len(records)} records from {pass1_inputs_path}")
    print(f"Backend: {args.backend}")
    print(f"Reading dir: {reading_dir}")

    pass1_results = load_json_array(pass1_output_path)
    if args.stage in ("both", "pass1"):
        pass1_results = process_pass1(records, args, pass1_output_path)
        print(f"Saved pass1 results: {pass1_output_path} ({len(pass1_results)} rows)")
    elif not pass1_results:
        print(f"ERROR: pass2 requires existing {pass1_output_path}", file=sys.stderr)
        return 1

    if args.stage in ("both", "pass2"):
        pass2_results = process_pass2(records, pass1_results, args, pass2_output_path)
        print(f"Saved pass2 results: {pass2_output_path} ({len(pass2_results)} rows)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
