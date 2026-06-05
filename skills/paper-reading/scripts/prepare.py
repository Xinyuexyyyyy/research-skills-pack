#!/usr/bin/env python3
"""
prepare.py — Prepare LLM inputs for Pass 1 & Pass 2 evidence extraction.

Reads study_selection.csv + candidate_papers.csv, generates structured prompt
inputs as JSONL. The LLM (Claude) processes these inputs; results are later
collected by collect.py.

Usage:
  python3 prepare.py <run_dir>

Input files (in <run_dir>/):
  study_selection_v*.csv    — screening results with 'selection' column
  candidate_papers_v*.csv   — paper metadata (title, abstract, keywords)

Output files (in <run_dir>/reading/):
  pass1_inputs.jsonl        — one JSON object per include paper
  extraction_plan.csv       — planned channel per paper

Pipeline:
  1. Match include papers to candidate metadata
  2. Determine channel (abstract-only / arxiv / pending)
  3. Write pass1_inputs.jsonl with prompt context
"""
import csv
import json
import sys
from pathlib import Path
from collections import Counter
from common import (
    find_csv_in_dirs,
    is_include_row,
    load_effective_selection_rows,
    load_candidate_indexes,
    resolve_run_layout,
    resolve_selection_uid,
)


# Pass 1 schema fields expected from LLM output
PASS1_FIELDS = [
    "category", "context", "correctness_flag", "contributions",
    "clarity_score", "pass1_verdict", "pass1_confidence", "pass1_reason"
]

# Category candidates for prompt
CATEGORIES = [
    "review", "empirical_cfd", "empirical_material", "empirical_optimization",
    "empirical_ai", "theoretical", "survey"
]

# Abstract placeholder patterns
PLACEHOLDER_PATTERNS = [
    "available online only", "subscription required",
    "abstract not available", "abstract unavailable"
]

def is_placeholder_abstract(text: str) -> bool:
    """Check if abstract is a placeholder."""
    if not text:
        return True
    text_lower = text.strip().lower()
    if len(text_lower) < 50:
        return True
    for pat in PLACEHOLDER_PATTERNS:
        if pat in text_lower:
            return True
    return False


def determine_channel(paper_uid: str, abstract: str, arxiv_id: str) -> tuple:
    """Determine extraction channel and reason."""
    if paper_uid.startswith('arxiv:'):
        return 'arxiv', 'paper_uid is arxiv (ar5iv HTML or PDF)'
    if is_placeholder_abstract(abstract):
        reason = f'no_abstract (len={len(abstract or "")})'
        if arxiv_id:
            reason += f'; arxiv_id={arxiv_id}'
        return 'pending', reason
    return 'abstract-only', f'abstract len={len(abstract)}'


def build_pass1_input(paper: dict) -> dict:
    """Build a single Pass 1 input record."""
    return {
        "paper_uid": paper["paper_uid"],
        "title": paper.get("title", ""),
        "authors": paper.get("authors", ""),
        "year": paper.get("year", ""),
        "venue": paper.get("venue", ""),
        "doi": paper.get("doi", ""),
        "abstract": paper.get("abstract", ""),
        "keywords": paper.get("keywords", ""),
        "channel": paper["channel"],
        "expected_output_fields": PASS1_FIELDS,
        "category_candidates": CATEGORIES,
        "verdict_candidates": ["proceed_to_pass2", "demote_to_qualitative_only", "skip"]
    }


def main(argv):
    if len(argv) != 2:
        print("Usage: prepare.py <run_dir>", file=sys.stderr)
        return 2

    run_dir = Path(argv[1]).expanduser().resolve()
    if not run_dir.exists():
        print(f"ERROR: run_dir not found: {run_dir}", file=sys.stderr)
        return 1

    layout = resolve_run_layout(run_dir)

    # Find input files
    try:
        sel_path = find_csv_in_dirs([layout["screening_dir"], run_dir], "study_selection")
        cand_path = find_csv_in_dirs([layout["discovery_dir"], run_dir], "candidate_papers")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Input:  {sel_path.name}")
    print(f"Input:  {cand_path.name}")

    # Build candidate index
    cand_by_uid, cand_by_id, cand_by_title = load_candidate_indexes(cand_path)

    # Process include rows
    out_dir = layout["reading_dir"]
    out_dir.mkdir(exist_ok=True)

    pass1_inputs = []
    plan_rows = []
    skipped_abstract = 0
    unresolved = 0

    for row in load_effective_selection_rows(sel_path):
        if not is_include_row(row):
            continue

        uid, cd = resolve_selection_uid(row, cand_by_uid, cand_by_id, cand_by_title)
        if not cd:
            unresolved += 1
        abstract = (cd.get('abstract') or '').strip()
        arxiv_id = (cd.get('arxiv_id') or '').strip()

        channel, reason = determine_channel(uid, abstract, arxiv_id)

        plan_rows.append({
            'paper_uid': uid,
            'planned_channel': channel,
            'abstract_length': len(abstract),
            'has_arxiv_id': 'yes' if arxiv_id else 'no',
            'notes': reason,
        })

        if channel == 'pending':
            skipped_abstract += 1
            continue

        # Build input with merged data
        merged = {**cd, **row}
        merged['paper_uid'] = uid
        merged['channel'] = channel
        pass1_inputs.append(build_pass1_input(merged))

    # Write pass1_inputs.jsonl
    pass1_path = out_dir / "pass1_inputs.jsonl"
    with pass1_path.open('w', encoding='utf-8') as f:
        for item in pass1_inputs:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # Write extraction_plan.csv
    plan_path = out_dir / "extraction_plan.csv"
    with plan_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'paper_uid', 'planned_channel', 'abstract_length', 'has_arxiv_id', 'notes'
        ])
        writer.writeheader()
        writer.writerows(plan_rows)

    # Stats
    counts = Counter(r['planned_channel'] for r in plan_rows)
    total = len(plan_rows)
    print(f"\nTotal include: {total}")
    for ch, n in sorted(counts.items()):
        pct = n * 100 // total if total else 0
        print(f"  {ch}: {n} ({pct}%)")
    print(f"\nPass 1 inputs: {len(pass1_inputs)} (pending: {skipped_abstract})")
    if unresolved:
        print(f"Unresolved candidate joins: {unresolved}")
    print(f"Output: {pass1_path}")
    print(f"Output: {plan_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
