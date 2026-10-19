#!/usr/bin/env python3
"""Today's URLs to request indexing for in Google Search Console (about 10 a day is Google's limit).

Reads the latest indexing snapshot (snapshots/index-<date>.json, written by weekly_report.py) and lists
pages Google has not indexed yet, money pages first: hotels/products, then destinations/categories, then
list pages and the home page, then guides; legal pages last. URLs requested in the last 14 days are skipped.

Usage:
    python indexing_queue.py example.com            # print today's 10
    python indexing_queue.py example.com -n 15
    python indexing_queue.py example.com --mark     # also record today's list as requested
    python indexing_queue.py example.com --json
Requested URLs are kept in data/indexing-requested.json ({url: date}).
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import CLIENTS_DIR, load_json, normalize_domain  # noqa: E402

SKIP_DAYS = 14


def priority(url: str) -> tuple:
    path = "/" + url.split("://", 1)[-1].split("/", 1)[-1]
    lang = 1 if path.startswith("/ar/") else 0
    p = path[3:] if lang else path
    if p.startswith(("/privacy", "/terms")):
        rank = 9
    elif p.startswith(("/hotels/", "/products/", "/product/")) and p.count("/") > 2:
        rank = 0
    elif p.startswith(("/destinations/", "/collections/", "/category/")) and p.count("/") > 2:
        rank = 1
    elif p in ("/", "/hotels/", "/destinations/", "/contact/", "/about/", "/faq/"):
        rank = 2
    else:
        rank = 3
    return (rank, lang, path)


def queue(domain: str, n: int = 10) -> dict:
    folder = CLIENTS_DIR / normalize_domain(domain)
    snaps = sorted((folder / "snapshots").glob("index-*.json"))
    if not snaps:
        return {"error": "No indexing snapshot yet: run weekly_report.py first."}
    snap = load_json(snaps[-1])
    requested_file = folder / "data" / "indexing-requested.json"
    requested = load_json(requested_file) if requested_file.exists() else {}
    cutoff = (dt.date.today() - dt.timedelta(days=SKIP_DAYS)).isoformat()
    pending = [u for u, state in snap.get("index", {}).items()
               if not str(state).startswith("Submitted and indexed") and requested.get(u, "") < cutoff]
    pending.sort(key=priority)
    return {"snapshot": snaps[-1].name, "not_indexed": len(pending), "today": pending[:n],
            "requested_file": str(requested_file), "requested": requested}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--mark", action="store_true", help="record today's list as requested")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    q = queue(a.client, a.n)
    if "error" in q:
        sys.exit(q["error"])
    if a.mark:
        today = dt.date.today().isoformat()
        q["requested"].update({u: today for u in q["today"]})
        Path(q["requested_file"]).write_text(json.dumps(q["requested"], indent=1), encoding="utf-8")
    if a.json:
        print(json.dumps({k: q[k] for k in ("snapshot", "not_indexed", "today")}, indent=1))
        return
    print(f"Not indexed (and not requested in the last {SKIP_DAYS} days): {q['not_indexed']} - from {q['snapshot']}")
    print("Search Console > URL Inspection > paste > Request indexing:\n")
    print("\n".join(q["today"]))
    if a.mark:
        print("\nMarked as requested today.")


if __name__ == "__main__":
    main()
