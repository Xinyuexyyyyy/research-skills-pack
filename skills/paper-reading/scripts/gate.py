#!/usr/bin/env python3
"""
gate.py — Run three-layer Quality Gate for paper-reading outputs.

Checks Pass 1 proceed ratio, Pass 2 evidence completeness, and cross-file
integrity. Fails fast (non-zero exit) if any gate is broken.

Usage:
  python3 gate.py <run_dir>

Exit codes:
  0 — all gates PASS
  1 — gate failure or missing files
  2 — usage error
"""
import csv
import json
import sys
from pathlib import Path
from common import find_csv_in_dirs, load_effective_selection_rows, resolve_run_layout


def count_rows(path: Path) -> int:
    """Count data rows (excluding header) in CSV."""
    if not path.exists():
        return 0
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return sum(1 for _ in reader)


def load_uids(path: Path) -> set:
    """Load paper_uid column as a set."""
    if not path.exists():
        return set()
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {row['paper_uid'] for row in reader if row.get('paper_uid')}


def load_json(path: Path) -> list:
    """Load JSON array or return empty list."""
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def count_include_rows(path: Path) -> int:
    """Count effective rows where selection/decision=include."""
    return sum(
        1
        for row in load_effective_selection_rows(path)
        if (row.get('selection') or row.get('decision') or '').strip().lower() == 'include'
    )


def check_overlap(*uid_sets: set) -> list:
    """Find overlapping UIDs across sets."""
    all_uids = set()
    for s in uid_sets:
        all_uids |= s
    overlaps = []
    for uid in all_uids:
        containing = [i for i, s in enumerate(uid_sets) if uid in s]
        if len(containing) > 1:
            overlaps.append((uid, containing))
    return overlaps


def main(argv):
    if len(argv) != 2:
        print("Usage: gate.py <run_dir>", file=sys.stderr)
        return 2

    run_dir = Path(argv[1]).expanduser().resolve()
    layout = resolve_run_layout(run_dir)
    reading_dir = layout["reading_dir"]

    if not reading_dir.exists():
        print(f"ERROR: reading dir not found: {reading_dir}", file=sys.stderr)
        return 1

    try:
        sel_path = find_csv_in_dirs([layout["screening_dir"], run_dir], "study_selection")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    evidence_path = reading_dir / "evidence_table.csv"
    pending_path = reading_dir / "pending_fulltext.csv"
    low_conf_path = reading_dir / "low_confidence_evidence.csv"
    pass1_path = reading_dir / "pass1_results.json"
    pass2_path = reading_dir / "pass2_results.json"

    for p in [evidence_path, pending_path]:
        if not p.exists():
            print(f"ERROR: required file missing: {p}", file=sys.stderr)
            return 1

    include_total = count_include_rows(sel_path)
    evidence_count = count_rows(evidence_path)
    pending_count = count_rows(pending_path)
    low_conf_count = count_rows(low_conf_path)
    processed_total = evidence_count + pending_count + low_conf_count

    evidence_uids = load_uids(evidence_path)
    pending_uids = load_uids(pending_path)
    low_conf_uids = load_uids(low_conf_path)
    pass1_results = load_json(pass1_path)
    pass2_results = load_json(pass2_path)

    print("=" * 50)
    print("Paper Reading — Quality Gate Report")
    print("=" * 50)
    print(f"\nRow counts:")
    print(f"  study_selection include: {include_total}")
    print(f"  evidence_table:          {evidence_count}")
    print(f"  pending_fulltext:        {pending_count}")
    print(f"  low_confidence:          {low_conf_count}")
    print(f"  processed total:         {processed_total}")

    # Gate 1
    if pass1_results:
        pass1_non_skip = sum(
            1 for row in pass1_results
            if row.get('pass1_verdict') in ('proceed_to_pass2', 'demote_to_qualitative_only')
        )
    else:
        pass1_non_skip = evidence_count + low_conf_count
    gate1_ratio = pass1_non_skip / include_total * 100 if include_total else 0
    gate1_pass = gate1_ratio >= 60.0
    print(f"\n{'─' * 50}")
    print(f"Gate 1 — Pass 1 non-skip ratio: {gate1_ratio:.1f}% (threshold 60%) — {'PASS' if gate1_pass else 'FAIL'}")

    # Gate 2
    if pass2_results:
        gate2_denom = len(pass2_results)
        gate2_num = sum(
            1 for row in pass2_results
            if row.get('extraction_confidence') in ('high', 'medium')
        )
    else:
        gate2_denom = evidence_count + low_conf_count
        gate2_num = evidence_count
    gate2_ratio = gate2_num / gate2_denom * 100 if gate2_denom else 0
    gate2_pass = gate2_ratio >= 80.0
    print(f"Gate 2 — Pass 2 completeness:  {gate2_ratio:.1f}% (threshold 80%) — {'PASS' if gate2_pass else 'FAIL'}")

    # Gate 3
    gate3_pass = processed_total == include_total
    print(f"Gate 3 — Integrity:           {'MATCH' if gate3_pass else f'MISMATCH (delta={processed_total - include_total})'} — {'PASS' if gate3_pass else 'FAIL'}")

    # Check 4
    overlaps = check_overlap(evidence_uids, pending_uids, low_conf_uids)
    overlap_pass = len(overlaps) == 0
    if overlaps:
        print(f"Check 4 — Overlaps:           {len(overlaps)} overlapping — FAIL")
    else:
        print(f"Check 4 — Overlaps:           none — PASS")

    all_pass = gate1_pass and gate2_pass and gate3_pass and overlap_pass
    print(f"\n{'=' * 50}")
    print(f"OVERALL: {'ALL GATES PASS' if all_pass else 'GATE FAILURE'}")
    print("=" * 50)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
