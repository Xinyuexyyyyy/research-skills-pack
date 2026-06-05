#!/usr/bin/env python3
"""
collect.py — Collect LLM outputs and write all paper-reading artifacts.

Reads Pass 1 & Pass 2 JSON results (from LLM), merges with metadata,
and produces the full artifact suite: evidence_table.csv, pending_fulltext.csv,
low_confidence_evidence.csv, evidence_audit.md, reading_summary.md.

Usage:
  python3 collect.py <run_dir>

Input files (in <run_dir>/reading/):
  pass1_results.json      — LLM Pass 1 output (array of JSON objects)
  pass2_results.json      — LLM Pass 2 output (array of JSON objects, optional)

Output files (in <run_dir>/reading/):
  evidence_table.csv           — 22-column structured evidence
  pending_fulltext.csv         — skipped papers
  low_confidence_evidence.csv  — low-confidence extractions
  evidence_audit.md            — per-paper audit trail
  reading_summary.md           — human-readable summary

Pass 1 result schema (per item):
  {
    "paper_uid": "...",
    "category": "...",
    "context": "...",
    "correctness_flag": "valid",
    "contributions": ["..."],
    "clarity_score": "well_written",
    "pass1_verdict": "proceed_to_pass2",
    "pass1_confidence": "high",
    "pass1_reason": "..."
  }

Pass 2 result schema (per item):
  {
    "paper_uid": "...",
    "population": "...",
    "intervention": "...",
    "comparator": "...",
    "outcome": "...",
    "method": "...",
    "key_finding_1": "...",
    "key_finding_2": "...",
    "key_finding_3": "...",
    "extraction_confidence": "high",
    "extraction_source": "abstract"
  }
"""
import csv
import json
import sys
from pathlib import Path
from collections import Counter
from common import resolve_run_layout


# evidence_table columns (22 total)
EVIDENCE_FIELDS = [
    'paper_uid',
    'category', 'context', 'correctness_flag', 'contributions',
    'clarity_score', 'pass1_verdict', 'pass1_confidence',
    'population', 'intervention', 'comparator', 'outcome',
    'method', 'key_finding_1', 'key_finding_2', 'key_finding_3',
    'extraction_confidence', 'extraction_source', 'qualitative_only',
    'hidden_assumptions', 'limitations', 'future_work'
]

PENDING_FIELDS = ['paper_uid', 'reason_code', 'suggested_route', 'pass1_notes']
LOW_CONFIDENCE_FIELDS = ['paper_uid', 'low_confidence_reason', 'partial_evidence', 'suggested_action']


def load_json(path: Path) -> list:
    """Load JSON array from file."""
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def contributions_to_string(contributions) -> str:
    """Convert contributions list to semicolon-separated string."""
    if isinstance(contributions, list):
        return '; '.join(str(c) for c in contributions if c)
    return str(contributions) if contributions else ''


def build_evidence_row(p1: dict, p2: dict) -> dict:
    """Merge Pass 1 + Pass 2 into a single evidence row."""
    row = {'paper_uid': p1.get('paper_uid', '')}

    # Pass 1 fields
    for f in ['category', 'context', 'correctness_flag', 'clarity_score',
              'pass1_verdict', 'pass1_confidence']:
        row[f] = p1.get(f, '')

    row['contributions'] = contributions_to_string(p1.get('contributions', []))

    # qualitative_only flag
    is_review = p1.get('category') in ('review', 'survey')
    is_demote = p1.get('pass1_verdict') == 'demote_to_qualitative_only'
    row['qualitative_only'] = 'true' if (is_review or is_demote) else 'false'

    # Pass 2 fields (if available)
    if p2:
        for f in ['population', 'intervention', 'comparator', 'outcome',
                  'method', 'key_finding_1', 'key_finding_2', 'key_finding_3',
                  'extraction_confidence', 'extraction_source']:
            row[f] = p2.get(f, '')
    else:
        for f in ['population', 'intervention', 'comparator', 'outcome',
                  'method', 'key_finding_1', 'key_finding_2', 'key_finding_3',
                  'extraction_confidence', 'extraction_source']:
            row[f] = ''

    # Pass 3 fields (empty in P0)
    for f in ['hidden_assumptions', 'limitations', 'future_work']:
        row[f] = ''

    return row


def determine_pending_reason(p1: dict) -> tuple:
    """Determine reason_code and suggested_route for pending papers."""
    verdict = p1.get('pass1_verdict', '')
    uid = p1.get('paper_uid', '')

    if verdict == 'skip':
        reason = 'NO_ABSTRACT'
        if uid.startswith('arxiv:'):
            route = 'arxiv_only'
        else:
            route = 'unpaywall'
    else:
        reason = 'UNKNOWN'
        route = 'give_up'

    notes = p1.get('pass1_reason', '')
    return reason, route, notes


def determine_low_confidence_reason(p2: dict) -> tuple:
    """Determine why extraction confidence is low."""
    missing = []
    for f in ['population', 'intervention', 'method']:
        if not p2.get(f, '').strip():
            missing.append(f.upper())

    if missing:
        reason = 'MISSING_' + '_'.join(missing)
    elif not p2.get('outcome', '').strip():
        reason = 'MISSING_OUTCOME'
    else:
        reason = 'ABSTRACT_TOO_SHORT'

    # Build partial evidence JSON
    partial = {}
    for f in ['population', 'intervention', 'outcome', 'method']:
        v = p2.get(f, '')
        if v:
            partial[f] = v

    action = 'fetch_fulltext' if p2.get('extraction_source') == 'title_only' else 'demote_to_qualitative'
    return reason, json.dumps(partial, ensure_ascii=False), action


def write_evidence_csv(path: Path, rows: list):
    """Write evidence_table.csv."""
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=EVIDENCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_pending_csv(path: Path, rows: list):
    """Write pending_fulltext.csv."""
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=PENDING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_low_confidence_csv(path: Path, rows: list):
    """Write low_confidence_evidence.csv."""
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=LOW_CONFIDENCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_audit_md(path: Path, pass1_results: list, pass2_results: list, evidence_rows: list, pending_rows: list, low_conf_rows: list):
    """Write evidence_audit.md."""
    lines = ['# Evidence Audit\n', '> 每条 evidence 的 Pass 分层审计记录。\n\n']

    for row in evidence_rows:
        uid = row['paper_uid']
        lines.append(f'## {uid}\n')

        # Pass 1
        lines.append('### Pass 1 审计\n')
        lines.append(f"- **五问:** category={row['category']} | context={row['context'][:60]}... | correctness={row['correctness_flag']} | clarity={row['clarity_score']}\n")
        lines.append(f"- **贡献:** {row['contributions'][:100]}...\n")
        lines.append(f"- **裁决:** {row['pass1_verdict']} (confidence={row['pass1_confidence']})\n")
        lines.append('\n')

        # Pass 2
        lines.append('### Pass 2 审计\n')
        pico = f"P={row['population'][:40] or '-'} | I={row['intervention'][:40] or '-'} | C={row['comparator'][:40] or '-'} | O={row['outcome'][:40] or '-'}"
        lines.append(f"- **PICO:** {pico}\n")
        lines.append(f"- **方法:** {row['method'][:80] or '-'}\n")
        lines.append(f"- **发现:** {row['key_finding_1'][:80] or '-'}\n")
        lines.append(f"- **置信度:** {row['extraction_confidence']} | source={row['extraction_source']} | qualitative_only={row['qualitative_only']}\n")
        lines.append('\n---\n')

    # Summary
    verdict_counts = Counter(r.get('pass1_verdict', '') for r in pass1_results)
    pass2_success = sum(1 for r in pass2_results if r.get('extraction_confidence') in ('high', 'medium'))
    lines.append('## 跨文件总结\n\n')
    lines.append(f"- **Pass 1 proceed:** {verdict_counts.get('proceed_to_pass2', 0)}\n")
    lines.append(f"- **Pass 1 demote:** {verdict_counts.get('demote_to_qualitative_only', 0)}\n")
    lines.append(f"- **Pass 1 skip:** {verdict_counts.get('skip', 0)}\n")
    lines.append(f"- **Pass 2 evidence:** {pass2_success}\n")
    lines.append(f"- **Pass 2 low confidence:** {len(low_conf_rows)}\n")
    lines.append(f"- **Pending:** {len(pending_rows)}\n")
    lines.append('\n')

    with path.open('w', encoding='utf-8') as f:
        f.writelines(lines)


def write_summary_md(path: Path, pass1_results: list, pass2_results: list, evidence_rows: list, pending_rows: list, low_conf_rows: list):
    """Write reading_summary.md."""
    total_include = len(evidence_rows) + len(pending_rows) + len(low_conf_rows)
    verdict_counts = Counter(r.get('pass1_verdict', '') for r in pass1_results)
    pass1_proceed = verdict_counts.get('proceed_to_pass2', 0)
    pass1_demote = verdict_counts.get('demote_to_qualitative_only', 0)
    pass1_non_skip = pass1_proceed + pass1_demote
    pass2_complete = sum(1 for r in pass2_results if r.get('extraction_confidence') in ('high', 'medium'))
    pass2_attempted = len(pass2_results)

    gate1 = pass1_non_skip / total_include * 100 if total_include else 0
    gate2 = pass2_complete / pass2_attempted * 100 if pass2_attempted else 0

    conf_counts = Counter(r.get('extraction_confidence', '') for r in pass2_results)

    lines = [
        '# Reading Summary\n\n',
        'delivery_mode=reading-only\n\n',
        f'> Pass 1 + Pass 2 evidence extraction results. {total_include} papers total.\n\n',
        '---\n\n',
        '## 一、Pass 1 扫描结果\n\n',
        f'**{total_include} 篇论文扫描完成:**\n\n',
        '| 裁决 | 数量 |\n',
        '|------|------|\n',
        f'| proceed_to_pass2 | {pass1_proceed} |\n',
        f'| demote_to_qualitative_only | {pass1_demote} |\n',
        f'| skip | {len(pending_rows)} |\n',
        f'| Pass 1 non-skip ratio | {gate1:.1f}% |\n\n',
        '---\n\n',
        '## 二、Pass 2 抽取结果\n\n',
        f'**{pass2_complete} 篇论文 evidence 抽取完成:**\n\n',
        '| 置信度 | 数量 |\n',
        '|--------|------|\n',
        f'| high | {conf_counts.get("high", 0)} |\n',
        f'| medium | {conf_counts.get("medium", 0)} |\n',
        f'| low (不进主表) | {len(low_conf_rows)} |\n',
        f'\n抽取率: {pass2_complete}/{pass2_attempted or 0} = **{gate2:.1f}%** (门槛 80%)\n\n',
        '---\n\n',
        '## 三、下一步建议\n\n',
        f'1. **Quality Gate 1:** {gate1:.1f}% (门槛 60%) — {"PASS" if gate1 >= 60 else "FAIL"}\n',
        f'2. **Quality Gate 2:** {gate2:.1f}% (门槛 80%) — {"PASS" if gate2 >= 80 else "FAIL"}\n',
        f'3. **Pending 论文:** {len(pending_rows)} 篇需全文通路\n',
        '\n',
    ]

    with path.open('w', encoding='utf-8') as f:
        f.writelines(lines)


def ensure_empty_csv(path: Path, fieldnames: list):
    """Write an empty CSV with header if there are no rows."""
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()


def main(argv):
    if len(argv) != 2:
        print("Usage: collect.py <run_dir>", file=sys.stderr)
        return 2

    run_dir = Path(argv[1]).expanduser().resolve()
    layout = resolve_run_layout(run_dir)
    reading_dir = layout["reading_dir"]

    if not reading_dir.exists():
        print(f"ERROR: reading dir not found: {reading_dir}", file=sys.stderr)
        return 1

    # Load LLM results
    pass1_results = load_json(reading_dir / "pass1_results.json")
    pass2_results = load_json(reading_dir / "pass2_results.json")

    # Index Pass 2 results by paper_uid
    pass2_by_uid = {r['paper_uid']: r for r in pass2_results if 'paper_uid' in r}

    # Categorize
    evidence_rows = []
    pending_rows = []
    low_confidence_rows = []

    for p1 in pass1_results:
        if 'paper_uid' not in p1:
            continue

        verdict = p1.get('pass1_verdict', '')

        if verdict == 'skip':
            reason, route, notes = determine_pending_reason(p1)
            pending_rows.append({
                'paper_uid': p1['paper_uid'],
                'reason_code': reason,
                'suggested_route': route,
                'pass1_notes': notes,
            })
            continue

        # Pass 1 = proceed or demote
        p2 = pass2_by_uid.get(p1['paper_uid'], {})
        row = build_evidence_row(p1, p2)

        # Check if low confidence
        if p2 and p2.get('extraction_confidence') == 'low':
            reason, partial, action = determine_low_confidence_reason(p2)
            low_confidence_rows.append({
                'paper_uid': p1['paper_uid'],
                'low_confidence_reason': reason,
                'partial_evidence': partial,
                'suggested_action': action,
            })
        else:
            evidence_rows.append(row)

    # Write outputs
    write_evidence_csv(reading_dir / "evidence_table.csv", evidence_rows)
    write_pending_csv(reading_dir / "pending_fulltext.csv", pending_rows)
    if low_confidence_rows:
        write_low_confidence_csv(reading_dir / "low_confidence_evidence.csv", low_confidence_rows)
    else:
        ensure_empty_csv(reading_dir / "low_confidence_evidence.csv", LOW_CONFIDENCE_FIELDS)
    write_audit_md(reading_dir / "evidence_audit.md", pass1_results, pass2_results, evidence_rows, pending_rows, low_confidence_rows)
    write_summary_md(reading_dir / "reading_summary.md", pass1_results, pass2_results, evidence_rows, pending_rows, low_confidence_rows)

    # Stats
    print(f"Evidence table:    {len(evidence_rows)} rows")
    print(f"Pending:           {len(pending_rows)} rows")
    print(f"Low confidence:    {len(low_confidence_rows)} rows")
    print(f"Total processed:   {len(evidence_rows) + len(pending_rows) + len(low_confidence_rows)}")
    print(f"\nOutputs in: {reading_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
