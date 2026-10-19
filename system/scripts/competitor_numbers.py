#!/usr/bin/env python3
"""Free size and strength numbers for a list of domains (competitors + the client).

Sources (all free):
    Tranco          global popularity rank, no key (lower = bigger site)
    Open PageRank   0-10 authority score + referring domains (free OPR key)
    CrUX            whether Chrome has real-user data for the site (a traffic
                    signal) and its Core Web Vitals (Google API key)
    Moz             Domain Authority + linking domains, only with --moz
                    (small free monthly quota, so it is opt-in)

Usage:
    python competitor_numbers.py a.com b.com c.com --json
    python competitor_numbers.py a.com b.com --moz --save client.com
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import (  # noqa: E402
    BACKLINKS_CONFIG, CLIENTS_DIR, GOOGLE_CONFIG, http_json, load_json,
    normalize_domain, run_seo_script,
)

TRANCO_API = "https://tranco-list.eu/api/ranks/domain/"
OPR_API = "https://openpagerank.keywordseverywhere.com/v1/domains/bulk"
CRUX_API = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def tranco_rank(domain: str):
    code, out = http_json(TRANCO_API + domain)
    if code != 200 or not isinstance(out, dict):
        return None
    ranks = sorted(out.get("ranks") or [], key=lambda r: r.get("date", ""), reverse=True)
    return ranks[0]["rank"] if ranks else None


def opr_numbers(domains: list) -> dict:
    key = load_json(BACKLINKS_CONFIG).get("keywordseverywhere_api_key")
    if not key:
        return {}
    out_map = {}
    for i in range(0, len(domains), 100):
        code, out = http_json(OPR_API, "POST", {"domains": domains[i:i + 100], "include_history": False},
                              {"Authorization": f"Bearer {key.strip()}"})
        if code != 200 or not isinstance(out, dict):
            continue
        for r in out.get("results", []):
            out_map[normalize_domain(r.get("domain", ""))] = {
                "opr_found": r.get("found", True),
                "open_page_rank": r.get("open_page_rank") if r.get("found", True) else None,
                "referring_domains": r.get("referring_domains"),
            }
    return out_map


def crux_numbers(domain: str):
    key = load_json(GOOGLE_CONFIG).get("api_key")
    if not key or not key.isascii():
        return None
    for origin in (f"https://www.{domain}", f"https://{domain}"):
        code, out = http_json(f"{CRUX_API}?key={key}", "POST", {"origin": origin})
        if code == 200 and isinstance(out, dict):
            metrics = out.get("record", {}).get("metrics", {})

            def p75(name):
                return metrics.get(name, {}).get("percentiles", {}).get("p75")
            return {"has_field_data": True, "origin": origin,
                    "lcp_p75_ms": p75("largest_contentful_paint"),
                    "inp_p75_ms": p75("interaction_to_next_paint"),
                    "cls_p75": p75("cumulative_layout_shift")}
    return {"has_field_data": False}


def moz_numbers(domain: str):
    if not load_json(BACKLINKS_CONFIG).get("moz_api_key"):
        return None
    code, out = run_seo_script("moz_api.py", "metrics", domain, "--json")
    data = out.get("data") if isinstance(out, dict) else None
    if not isinstance(data, dict):
        return {"error": str(out)[:150]}
    return {"domain_authority": data.get("domain_authority"),
            "linking_root_domains": data.get("linking_root_domains"),
            "spam_score": data.get("spam_score")}


def collect(domains: list, use_moz: bool) -> dict:
    domains = list(dict.fromkeys(normalize_domain(d) for d in domains if d.strip()))
    opr = opr_numbers(domains)
    rows = []
    for d in domains:
        rows.append({
            "domain": d,
            "tranco_rank": tranco_rank(d),
            **opr.get(d, {"opr_found": None, "open_page_rank": None, "referring_domains": None}),
            "crux": crux_numbers(d),
            "moz": moz_numbers(d) if use_moz else None,
        })
        time.sleep(1.1)  # Tranco asks for at most one query per second
    return {
        "date": datetime.date.today().isoformat(),
        "sources": {
            "tranco": True,
            "open_pagerank": bool(opr),
            "crux": bool(load_json(GOOGLE_CONFIG).get("api_key")),
            "moz": use_moz and bool(load_json(BACKLINKS_CONFIG).get("moz_api_key")),
        },
        "rows": rows,
    }


def as_markdown(report: dict) -> str:
    lines = ["| Domain | Tranco rank | Open PageRank | Referring domains | Chrome real-user data | Moz DA |",
             "|---|---|---|---|---|---|"]
    for r in report["rows"]:
        crux = r["crux"]
        crux_txt = "n/a (no Google key)" if crux is None else ("yes" if crux["has_field_data"] else "no")
        moz = r["moz"] or {}
        # opr_found False = too small to be in Common Crawl's link graph; missing key = n/a
        opr_missing = "not scored" if r.get("opr_found") is False else "n/a"
        rank = f"{r['tranco_rank']:,}" if r["tranco_rank"] else "not ranked"
        lines.append(f"| {r['domain']} | {rank} | "
                     f"{r['open_page_rank'] if r['open_page_rank'] is not None else opr_missing} | "
                     f"{r['referring_domains'] if r['referring_domains'] is not None else opr_missing} | "
                     f"{crux_txt} | {moz.get('domain_authority', 'n/a') if r['moz'] else 'n/a'} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domains", nargs="+")
    ap.add_argument("--moz", action="store_true", help="Also spend Moz free quota (1 row per domain)")
    ap.add_argument("--save", metavar="CLIENT", help="Save JSON into clients/CLIENT/data/")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = collect(args.domains, args.moz)
    if args.save:
        folder = CLIENTS_DIR / normalize_domain(args.save) / "data"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"competitor-numbers-{report['date']}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["saved_to"] = str(path)
    print(json.dumps(report, indent=2) if args.json else as_markdown(report))


if __name__ == "__main__":
    main()
