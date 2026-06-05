#!/usr/bin/env python3
"""
Abstract Pipeline — 综合 abstract 降级链工具。

实现 `paper-reading/SKILL.md` "Abstract 缺失降级链" 协议：
  1. Elsevier API (如果是 Elsevier DOI + ELSEVIER_API_KEY 存在)
  2. OpenAlex (重建 abstract_inverted_index)
  3. Semantic Scholar no-key DOI 端点
  4. Crossref (message.abstract，少数 publisher 提交)
  5. 标 needs_websearch（由 LLM 在 reading 阶段补，不在脚本里调）

用法
====

单点：
    python3 tools/abstract_pipeline.py 10.1016/j.fuel.2024.133091
    python3 tools/abstract_pipeline.py 10.1038/nature12373 --json

批量：
    python3 tools/abstract_pipeline.py \
        --batch <run>/00-discovery/candidate_papers.csv \
        --out <run>/00-discovery/abstracts_pipeline.json \
        --id-col id --doi-col doi --verbose

返回结构
========
{
  "doi": "...",
  "status": "ok" | "needs_websearch" | "no_doi",
  "source": "Elsevier API" | "OpenAlex" | "SS no-key" | "Crossref" | null,
  "abstract": "...",
  "abstract_chars": int,
  "title": "...",
  "venue": "...",
  "year": "...",
  "attempted": [{"source": "...", "status": "..."}, ...]
}
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Import elsevier_fetch from same directory
sys.path.insert(0, str(Path(__file__).parent))
try:
    from elsevier_fetch import fetch_abstract as _elsevier_fetch
    from elsevier_fetch import is_elsevier_doi
except ImportError as e:
    print(f"ERROR: cannot import elsevier_fetch: {e}", file=sys.stderr)
    sys.exit(2)


UA = "academic-research-pipeline/1.0 (mailto:research@example.com)"
TIMEOUT = 15


def _http_json(url: str, headers: dict = None):
    """Fetch URL, return parsed JSON or None."""
    headers = headers or {}
    headers.setdefault("User-Agent", UA)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}"}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"_error": f"net: {e}"}
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def fetch_via_openalex(doi: str) -> dict:
    """OpenAlex API — rebuild abstract from inverted_index."""
    url = f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?mailto=research@example.com"
    d = _http_json(url)
    if not d or "_error" in d:
        return {"status": "failed", "error": (d or {}).get("_error", "unknown")}
    idx = d.get("abstract_inverted_index")
    title = d.get("title") or ""
    year = str(d.get("publication_year") or "")
    venue = ""
    if d.get("primary_location"):
        venue = (d["primary_location"].get("source") or {}).get("display_name", "")
    if idx:
        pos = {}
        for word, plist in idx.items():
            for p in plist:
                pos[p] = word
        abstract = " ".join(pos[i] for i in sorted(pos))
        if len(abstract) > 50:
            return {"status": "ok", "abstract": abstract, "title": title, "venue": venue, "year": year}
    return {"status": "no_abstract", "title": title, "venue": venue, "year": year}


def fetch_via_ss_nokey(doi: str) -> dict:
    """Semantic Scholar (no key) — DOI endpoint."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=title,abstract,venue,year"
    d = _http_json(url)
    if not d or "_error" in d:
        # 429 / rate-limited
        return {"status": "failed", "error": (d or {}).get("_error", "unknown")}
    abstract = (d.get("abstract") or "").strip()
    title = d.get("title", "")
    venue = d.get("venue", "")
    year = str(d.get("year") or "")
    if len(abstract) > 50:
        return {"status": "ok", "abstract": abstract, "title": title, "venue": venue, "year": year}
    return {"status": "no_abstract", "title": title, "venue": venue, "year": year}


def fetch_via_crossref(doi: str) -> dict:
    """Crossref — message.abstract (少数 publisher 提交)."""
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    d = _http_json(url)
    if not d or "_error" in d:
        return {"status": "failed", "error": (d or {}).get("_error", "unknown")}
    msg = d.get("message", {})
    abstract = (msg.get("abstract") or "").strip()
    # Crossref abstract 经常带 <jats:p> 等标签，简单清洗
    import re
    abstract = re.sub(r"<[^>]+>", "", abstract).strip()
    title_list = msg.get("title", [])
    title = title_list[0] if title_list else ""
    venue_list = msg.get("container-title", [])
    venue = venue_list[0] if venue_list else ""
    year = ""
    issued = msg.get("issued", {}).get("date-parts", [[None]])
    if issued and issued[0] and issued[0][0]:
        year = str(issued[0][0])
    if len(abstract) > 50:
        return {"status": "ok", "abstract": abstract, "title": title, "venue": venue, "year": year}
    return {"status": "no_abstract", "title": title, "venue": venue, "year": year}


def fetch_pipeline(doi: str, api_key: str = None) -> dict:
    """
    Execute the abstract fallback pipeline:
        Elsevier → OpenAlex → SS no-key → Crossref → needs_websearch

    Returns dict with status / source / abstract / attempted (audit trail).
    """
    if not doi or not doi.strip():
        return {"doi": doi, "status": "no_doi", "source": None, "abstract": "", "abstract_chars": 0,
                "title": "", "venue": "", "year": "", "attempted": []}

    doi = doi.replace("https://doi.org/", "").strip()
    attempted = []

    # Step 1: Elsevier (only for 10.1016/*)
    if is_elsevier_doi(doi):
        r = _elsevier_fetch(doi, api_key=api_key)
        attempted.append({"source": "Elsevier API", "status": r["status"]})
        if r["status"] == "ok":
            return {"doi": doi, "status": "ok", "source": "Elsevier API",
                    "abstract": r["abstract"], "abstract_chars": r["abstract_chars"],
                    "title": r["title"], "venue": r["venue"], "year": r["year"],
                    "attempted": attempted}

    # Step 2: OpenAlex
    r = fetch_via_openalex(doi)
    attempted.append({"source": "OpenAlex", "status": r["status"]})
    if r["status"] == "ok":
        return {"doi": doi, "status": "ok", "source": "OpenAlex",
                "abstract": r["abstract"], "abstract_chars": len(r["abstract"]),
                "title": r["title"], "venue": r["venue"], "year": r["year"],
                "attempted": attempted}

    # Step 3: SS no-key
    r = fetch_via_ss_nokey(doi)
    attempted.append({"source": "SS no-key", "status": r["status"]})
    if r["status"] == "ok":
        return {"doi": doi, "status": "ok", "source": "SS no-key",
                "abstract": r["abstract"], "abstract_chars": len(r["abstract"]),
                "title": r["title"], "venue": r["venue"], "year": r["year"],
                "attempted": attempted}

    # Step 4: Crossref
    r = fetch_via_crossref(doi)
    attempted.append({"source": "Crossref", "status": r["status"]})
    if r["status"] == "ok":
        return {"doi": doi, "status": "ok", "source": "Crossref",
                "abstract": r["abstract"], "abstract_chars": len(r["abstract"]),
                "title": r["title"], "venue": r["venue"], "year": r["year"],
                "attempted": attempted}

    # Step 5: needs WebSearch (脚本不调 web，由 LLM 在 reading 阶段补)
    last_meta = r  # Crossref 通常有 metadata 即使没 abstract
    return {"doi": doi, "status": "needs_websearch", "source": None,
            "abstract": "", "abstract_chars": 0,
            "title": last_meta.get("title", ""), "venue": last_meta.get("venue", ""),
            "year": last_meta.get("year", ""),
            "attempted": attempted,
            "note": "All 4 APIs exhausted. paper-reading should call WebSearch with title+author+venue+year."}


def main():
    p = argparse.ArgumentParser(description="Abstract Pipeline — 综合降级链工具")
    p.add_argument("doi", nargs="?", help="Single DOI to fetch")
    p.add_argument("--batch", metavar="INPUT_CSV", help="Batch mode: read DOIs from CSV")
    p.add_argument("--out", metavar="OUTPUT_JSON", help="Batch output JSON path")
    p.add_argument("--id-col", default="id", metavar="COL", help="Batch: paper_id column (default: id)")
    p.add_argument("--doi-col", default="doi", metavar="COL", help="Batch: DOI column (default: doi)")
    p.add_argument("--key", help="Override ELSEVIER_API_KEY")
    p.add_argument("--json", action="store_true", help="Single mode: JSON only")
    p.add_argument("--verbose", "-v", action="store_true", help="Print progress to stderr")
    args = p.parse_args()

    if args.batch:
        with open(args.batch, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if args.id_col not in reader.fieldnames or args.doi_col not in reader.fieldnames:
                print(f"ERROR: column '{args.id_col}' or '{args.doi_col}' not in CSV. "
                      f"Available: {reader.fieldnames}", file=sys.stderr)
                sys.exit(2)
            items = [(r[args.id_col], (r.get(args.doi_col) or "").strip()) for r in reader if r.get(args.doi_col)]
        if args.verbose:
            print(f"Batch: {len(items)} DOIs", file=sys.stderr)
        results = {}
        sources_count = {}
        for i, (pid, doi) in enumerate(items, 1):
            r = fetch_pipeline(doi, api_key=args.key)
            results[pid] = r
            src = r.get("source") or "needs_websearch"
            sources_count[src] = sources_count.get(src, 0) + 1
            if args.verbose:
                mark = "✅" if r["status"] == "ok" else "❌"
                print(f"  [{i}/{len(items)}] paper_id={pid} {mark} {r['status']} via {src} "
                      f"({r['abstract_chars']} chars, tried {len(r['attempted'])} APIs)",
                      file=sys.stderr)
            time.sleep(0.3)
        out_json = json.dumps(results, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out_json)
            if args.verbose:
                print(f"\nSaved {len(results)} entries to {args.out}", file=sys.stderr)
                print(f"Source breakdown:", file=sys.stderr)
                for src, n in sorted(sources_count.items(), key=lambda x: -x[1]):
                    print(f"  {src}: {n}", file=sys.stderr)
        else:
            print(out_json)
        return

    if not args.doi:
        p.print_help()
        sys.exit(2)

    r = fetch_pipeline(args.doi, api_key=args.key)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    print(f"DOI:      {r['doi']}")
    print(f"Status:   {r['status']}")
    print(f"Source:   {r.get('source') or '(none - needs websearch)'}")
    if r["title"]:
        print(f"Title:    {r['title']}")
    if r["venue"]:
        print(f"Venue:    {r['venue']}  ({r['year']})")
    print(f"Attempted: ", end="")
    print(" → ".join(f"{a['source']}({a['status']})" for a in r["attempted"]))
    if r["abstract"]:
        print(f"\nAbstract ({r['abstract_chars']} chars):\n")
        print(r["abstract"])
    elif "note" in r:
        print(f"\nNote: {r['note']}")


if __name__ == "__main__":
    main()
