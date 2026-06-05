#!/usr/bin/env python3
"""
fetch_arxiv.py — Download arXiv preprint PDFs by arxiv ID.

Usage:
  python3 fetch_arxiv.py <arxiv_id> [<arxiv_id> ...]
  python3 fetch_arxiv.py 2403.10566

Output:
  Saves PDFs to ~/study-research/skills/paper-reading/data/fulltext/arxiv-<id>.pdf
  Skips download if file exists.
  Returns non-zero exit code on any failure.
"""
import sys
import urllib.request
import urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "fulltext"
ARXIV_PDF_BASE = "https://arxiv.org/pdf/{}.pdf"
TIMEOUT = 30
USER_AGENT = "study-research/paper-reading (academic research)"


def fetch_one(arxiv_id: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"arxiv-{arxiv_id}.pdf"
    if out.exists() and out.stat().st_size > 1024:
        return True, f"SKIP(exists, {out.stat().st_size} bytes): {out}"

    url = ARXIV_PDF_BASE.format(arxiv_id)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
        if len(data) < 1024:
            return False, f"FAIL(too-small {len(data)} bytes): {url}"
        if not data.startswith(b"%PDF"):
            return False, f"FAIL(not-pdf): {url}"
        out.write_bytes(data)
        return True, f"OK({len(data)} bytes): {out}"
    except urllib.error.HTTPError as e:
        return False, f"FAIL(http {e.code}): {url}"
    except Exception as e:
        return False, f"FAIL({type(e).__name__}: {e}): {url}"


def main(argv):
    if len(argv) < 2:
        print("Usage: fetch_arxiv.py <arxiv_id> [<arxiv_id> ...]", file=sys.stderr)
        return 2

    failures = 0
    for arxiv_id in argv[1:]:
        ok, msg = fetch_one(arxiv_id)
        print(f"[{arxiv_id}] {msg}")
        if not ok:
            failures += 1
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
