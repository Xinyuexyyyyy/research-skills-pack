#!/usr/bin/env python3
"""
Shared helpers for paper-reading scripts.

Keeps the P0 scripts compatible with both legacy run layouts:
  <run_dir>/study_selection*.csv
  <run_dir>/candidate_papers*.csv
  <run_dir>/reading/

and the newer structured layout:
  <run_dir>/00-discovery/candidate_papers*.csv
  <run_dir>/01-screening/study_selection*.csv
  <run_dir>/02-reading/
"""
from __future__ import annotations

import csv
from pathlib import Path


def resolve_run_layout(run_dir: Path) -> dict:
    """Resolve discovery/screening/reading directories for a run."""
    discovery_dir = run_dir / "00-discovery" if (run_dir / "00-discovery").exists() else run_dir
    screening_dir = run_dir / "01-screening" if (run_dir / "01-screening").exists() else run_dir

    if (run_dir / "02-reading").exists() or (run_dir / "01-screening").exists():
        reading_dir = run_dir / "02-reading"
    else:
        reading_dir = run_dir / "reading"

    return {
        "discovery_dir": discovery_dir,
        "screening_dir": screening_dir,
        "reading_dir": reading_dir,
    }


def find_csv_in_dirs(directories: list[Path], prefix: str) -> Path:
    """Find the newest versioned CSV across candidate directories."""
    matches = []
    seen = set()
    for directory in directories:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file() or path.suffix != ".csv":
                continue
            if not path.name.startswith(prefix):
                continue
            if path in seen:
                continue
            seen.add(path)
            matches.append(path)

    if not matches:
        looked = ", ".join(str(d) for d in directories)
        raise FileNotFoundError(f"No {prefix}*.csv found in: {looked}")

    matches.sort(key=lambda p: (len(p.name), p.name), reverse=True)
    return matches[0]


def normalize_selection_value(row: dict) -> str:
    """Normalize include/exclude decisions across old/new schemas."""
    value = (row.get("selection") or row.get("decision") or "").strip().lower()
    return value


def is_include_row(row: dict) -> bool:
    """Return True if the row is an include decision."""
    return normalize_selection_value(row) == "include"


def stage_rank(row: dict) -> int:
    """Rank screening stages so the latest effective decision wins."""
    stage = (row.get("screening_stage") or "").strip().lower()
    ranking = {
        "title_abstract": 1,
        "fulltext": 2,
        "final": 3,
        "": 3,
    }
    return ranking.get(stage, 0)


def load_effective_selection_rows(path: Path) -> list[dict]:
    """
    Load one effective screening row per paper.

    For multi-stage screening outputs, prefer the row with the highest stage rank
    so `final` decisions override `title_abstract`. For brief/legacy files with no
    stage column, the single row is treated as the effective final decision.
    """
    chosen = {}
    ordered_keys = []

    with path.open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            key = row.get("paper_uid") or row.get("id") or row.get("title") or ""
            if not key:
                continue
            if key not in chosen:
                chosen[key] = row
                ordered_keys.append(key)
                continue
            if stage_rank(row) >= stage_rank(chosen[key]):
                chosen[key] = row

    return [chosen[key] for key in ordered_keys]


def load_candidate_indexes(path: Path):
    """Load candidate metadata keyed by paper_uid, id, and title."""
    by_uid = {}
    by_id = {}
    by_title = {}

    with path.open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}

            paper_uid = row.get("paper_uid", "")
            paper_id = row.get("id", "")
            title = row.get("title", "")

            if paper_uid:
                by_uid[paper_uid] = row
            if paper_id:
                by_id[paper_id] = row
            if title:
                by_title[title] = row

    return by_uid, by_id, by_title


def resolve_selection_uid(row: dict, cand_by_uid: dict, cand_by_id: dict, cand_by_title: dict):
    """
    Resolve a selection row to the candidate metadata row.

    Supports:
    - modern screening rows where paper_uid is the true paper_uid
    - mixed rows where paper_uid actually stores the numeric candidate id
    - older rows with an explicit id column
    - last-resort exact title matches
    """
    candidates = []

    for key in ("paper_uid", "id"):
        value = (row.get(key) or "").strip()
        if value:
            candidates.append(value)

    for token in candidates:
        if token in cand_by_uid:
            paper = cand_by_uid[token]
            return paper.get("paper_uid") or token, paper
        if token in cand_by_id:
            paper = cand_by_id[token]
            return paper.get("paper_uid") or token, paper

    title = (row.get("title") or "").strip()
    if title and title in cand_by_title:
        paper = cand_by_title[title]
        return paper.get("paper_uid") or title, paper

    fallback = candidates[0] if candidates else title
    return fallback, {}
