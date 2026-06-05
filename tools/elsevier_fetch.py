#!/usr/bin/env python3
"""
Elsevier ScienceDirect API — abstract fetcher.

封装 2026-05-12 验证过的 Elsevier API 调用为可复用工具。
正确 endpoint: /content/article/doi/<DOI>  (不要用 /content/abstract/...)
实测对 Elsevier DOI (10.1016/*) = 100% 成功率，abstract 长度 955-2453 chars。

用法
====

单点 CLI：
    python3 tools/elsevier_fetch.py 10.1016/j.fuel.2024.133091
    python3 tools/elsevier_fetch.py 10.1016/j.fuel.2024.133091 --json   # 只输出 JSON

批量 CLI（从 CSV 读 DOI 列）：
    python3 tools/elsevier_fetch.py \
        --batch runs/2026-05-12_ammonia_fueled_si_engine/00-discovery/candidate_papers.csv \
        --out abstracts.json \
        --id-col id --doi-col doi

作为 Python 模块：
    from tools.elsevier_fetch import fetch_abstract, fetch_batch
    result = fetch_abstract("10.1016/j.fuel.2024.133091")
    print(result["abstract"])

环境变量
========
- `ELSEVIER_API_KEY`：必填。建议存于 `<workspace>/.env`（chmod 600 + .gitignore），通过 `source .env` 加载

返回结构
========
单点：{"doi", "status", "title", "abstract", "abstract_chars", "source", "endpoint", "venue", "year"}
status ∈ {"ok", "empty_abstract", "non_elsevier", "auth_error", "http_error", "network_error", "no_key"}

错误处理：脚本永远返回 JSON，永不 raise（除了 --key 都没设时）。
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request


ENDPOINT = "https://api.elsevier.com/content/article/doi/"


def is_elsevier_doi(doi: str) -> bool:
    """Elsevier 论文 DOI 几乎都以 10.1016/ 开头。"""
    if not doi:
        return False
    doi = doi.replace("https://doi.org/", "").strip()
    return doi.startswith("10.1016/")


def fetch_abstract(doi: str, api_key: str = None, timeout: int = 20) -> dict:
    """
    Fetch abstract for a single DOI from Elsevier ScienceDirect API.

    Args:
        doi: DOI string (with or without `https://doi.org/` prefix)
        api_key: Override env var ELSEVIER_API_KEY
        timeout: HTTP timeout in seconds

    Returns:
        dict with keys: doi, status, title, abstract, abstract_chars, source, endpoint, venue, year
    """
    api_key = api_key or os.environ.get("ELSEVIER_API_KEY")
    if not api_key:
        return _err(doi, "no_key", "ELSEVIER_API_KEY not set; pass --key or `source .env`")

    if not doi or not doi.strip():
        return _err(doi, "http_error", "Empty DOI")

    doi = doi.replace("https://doi.org/", "").strip()
    if not is_elsevier_doi(doi):
        return _err(doi, "non_elsevier", f"DOI prefix not 10.1016/* (Elsevier); got '{doi[:20]}'")

    url = f"{ENDPOINT}{doi}?apiKey={api_key}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        if e.code == 401 or e.code == 403:
            return _err(doi, "auth_error", f"HTTP {e.code}: {body}")
        return _err(doi, "http_error", f"HTTP {e.code}: {body}")
    except (urllib.error.URLError, TimeoutError) as e:
        return _err(doi, "network_error", str(e))
    except Exception as e:
        return _err(doi, "http_error", f"{type(e).__name__}: {e}")

    retr = data.get("full-text-retrieval-response", {})
    cd = retr.get("coredata", {})
    abstract = (cd.get("dc:description") or "").strip()
    title = cd.get("dc:title", "")
    venue = cd.get("prism:publicationName", "")
    cover_date = cd.get("prism:coverDate", "")
    year = cover_date[:4] if cover_date else ""

    if len(abstract) <= 50:
        return {
            "doi": doi, "status": "empty_abstract",
            "title": title, "abstract": "", "abstract_chars": 0,
            "source": "Elsevier API", "endpoint": "article/doi",
            "venue": venue, "year": year,
            "note": "API 返回成功但 abstract 字段为空。可能 in-press / just-accepted。"
        }

    return {
        "doi": doi, "status": "ok",
        "title": title, "abstract": abstract, "abstract_chars": len(abstract),
        "source": "Elsevier API", "endpoint": "article/doi",
        "venue": venue, "year": year,
    }


def _err(doi, status, msg):
    return {
        "doi": doi, "status": status, "title": "", "abstract": "",
        "abstract_chars": 0, "source": "Elsevier API", "endpoint": "article/doi",
        "venue": "", "year": "", "error": msg
    }


def fetch_batch(items: list, api_key: str = None, sleep: float = 0.4, verbose: bool = False) -> dict:
    """
    Batch fetch abstracts for a list of (paper_id, doi) tuples.

    Returns: {paper_id: <result dict from fetch_abstract>}
    """
    results = {}
    for i, (pid, doi) in enumerate(items, 1):
        result = fetch_abstract(doi, api_key=api_key)
        results[pid] = result
        if verbose:
            status = result["status"]
            chars = result.get("abstract_chars", 0)
            mark = "✅" if status == "ok" else "❌"
            print(f"  [{i}/{len(items)}] paper_id={pid} doi={doi[:40]}... {mark} {status} ({chars} chars)",
                  file=sys.stderr)
        time.sleep(sleep)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Elsevier ScienceDirect API — abstract fetcher",
        epilog="See tools/elsevier_fetch.py module docstring for usage examples.",
    )
    parser.add_argument("doi", nargs="?", help="Single DOI to fetch (e.g. 10.1016/j.fuel.2024.133091)")
    parser.add_argument("--batch", metavar="INPUT_CSV",
                        help="Batch mode: read DOIs from CSV column")
    parser.add_argument("--out", metavar="OUTPUT_JSON",
                        help="Batch mode output JSON path (default: stdout)")
    parser.add_argument("--id-col", default="id", metavar="COL",
                        help="Batch: column name for paper_id (default: id)")
    parser.add_argument("--doi-col", default="doi", metavar="COL",
                        help="Batch: column name for DOI (default: doi)")
    parser.add_argument("--key", help="Override ELSEVIER_API_KEY environment variable")
    parser.add_argument("--json", action="store_true",
                        help="Single mode: print only JSON (no pretty header)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print progress to stderr")
    args = parser.parse_args()

    if args.batch:
        # 批量模式
        with open(args.batch, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if args.id_col not in reader.fieldnames or args.doi_col not in reader.fieldnames:
                print(f"ERROR: column '{args.id_col}' or '{args.doi_col}' not in CSV. "
                      f"Available: {reader.fieldnames}", file=sys.stderr)
                sys.exit(2)
            items = [(row[args.id_col], (row.get(args.doi_col) or "").strip())
                     for row in reader if row.get(args.doi_col)]
        if args.verbose:
            print(f"Batch: {len(items)} DOIs to fetch", file=sys.stderr)
        results = fetch_batch(items, api_key=args.key, verbose=args.verbose)
        out_json = json.dumps(results, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out_json)
            ok = sum(1 for r in results.values() if r["status"] == "ok")
            if args.verbose:
                print(f"\nSaved {len(results)} entries to {args.out} ({ok} ok, {len(results)-ok} failed)",
                      file=sys.stderr)
        else:
            print(out_json)
        return

    # 单点模式
    if not args.doi:
        parser.print_help()
        sys.exit(2)

    result = fetch_abstract(args.doi, api_key=args.key)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Pretty 输出
    if result["status"] == "ok":
        print(f"DOI:      {result['doi']}")
        print(f"Title:    {result['title']}")
        print(f"Venue:    {result['venue']}  ({result['year']})")
        print(f"Source:   {result['source']}")
        print(f"Abstract ({result['abstract_chars']} chars):")
        print()
        print(result["abstract"])
    else:
        print(f"DOI:      {result['doi']}")
        print(f"Status:   {result['status']}")
        if "error" in result:
            print(f"Error:    {result['error']}")
        if "note" in result:
            print(f"Note:     {result['note']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
