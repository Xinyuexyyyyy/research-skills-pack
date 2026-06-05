#!/usr/bin/env python3
"""
make_extraction_plan.py — Generate extraction_plan.csv from study_selection + candidate_papers.

Decision logic (P0):
  - paper_uid starts with 'arxiv:' → channel='arxiv-2b' (ar5iv HTML, default fallback when no PDF parser)
  - otherwise: abstract field >= 50 chars → channel='abstract-only'
  - else → channel='pending' (reason_code=NO_ABSTRACT)

Usage:
  python3 make_extraction_plan.py <study_selection.csv> <candidate_papers.csv> <output_extraction_plan.csv>

Output columns:
  paper_uid, planned_channel, abstract_length, has_arxiv_id, notes
"""
import csv
import sys
from collections import Counter
from pathlib import Path


def main(argv):
    if len(argv) != 4:
        print("Usage: make_extraction_plan.py <study_selection.csv> <candidate_papers.csv> <output.csv>",
              file=sys.stderr)
        return 2

    sel_path, cand_path, out_path = map(Path, argv[1:])

    # 1. Build candidate index by paper_uid
    cand = {}
    with cand_path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            cand[row['paper_uid']] = row

    # 2. Iterate include rows
    plan_rows = []
    with sel_path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('selection') != 'include':
                continue
            uid = row['paper_uid']
            cd = cand.get(uid, {})
            abstract = (cd.get('abstract') or '').strip()
            arxiv_id = (cd.get('arxiv_id') or '').strip()

            if uid.startswith('arxiv:'):
                channel = 'arxiv-2b'
                reason = 'paper_uid starts with arxiv:'
            elif len(abstract) >= 50:
                channel = 'abstract-only'
                reason = f'abstract len={len(abstract)}'
            else:
                channel = 'pending'
                reason = f'no_abstract (len={len(abstract)}); arxiv_id={arxiv_id or "-"}'

            plan_rows.append({
                'paper_uid': uid,
                'planned_channel': channel,
                'abstract_length': len(abstract),
                'has_arxiv_id': 'yes' if arxiv_id else 'no',
                'notes': reason,
            })

    # 3. Write output
    with out_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['paper_uid', 'planned_channel', 'abstract_length', 'has_arxiv_id', 'notes']
        )
        writer.writeheader()
        writer.writerows(plan_rows)

    # 4. Stats
    counts = Counter(r['planned_channel'] for r in plan_rows)
    total = len(plan_rows)
    print(f"Total include: {total}")
    for ch, n in sorted(counts.items()):
        pct = n * 100 // total if total else 0
        print(f"  {ch}: {n} ({pct}%)")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
