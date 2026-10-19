#!/usr/bin/env python3
"""Score one round of AI-answer sampling for a client and compare it with the last round.

A round is a JSON list (one object per customer question) collected by Claude with web search:
    {"id", "question", "lang", "cited_domains": [...], "client_cited": bool,
     "client_mentioned": bool, "brands_mentioned": [...],
     "answer_gist", "answer_quality": "good|weak|none"}

Usage:
    python ai_visibility.py example.com round.json            # score, save, write report section
    python ai_visibility.py example.com round.json --json

It saves the round as clients/<domain>/data/ai-visibility-<date>.json and writes
clients/<domain>/reports/ai-visibility-<date>.md. client.json may list "competitor_domains".
This is a sample of AI web-search answers (free), not a full tracker of ChatGPT/Perplexity/AI Overviews.
"""

import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import CLIENTS_DIR, load_json, normalize_domain  # noqa: E402

AGGREGATORS = {"booking.com", "hotels.com", "expedia.com", "tripadvisor.com", "trip.com", "agoda.com", "kayak.com",
               "travelocity.com", "hotelscombined.com", "trivago.com", "priceline.com", "skyscanner.net", "almosafer.com",
               "wego.com", "halalbooking.com", "secretescapes.com"}


def flag(row, name):
    return bool(row.get(f"client_{name}", row.get(f"reservella_{name}", False)))


def score(rows, client, competitors):
    n = len(rows)
    cited = [r for r in rows if flag(r, "cited")]
    mentioned = [r for r in rows if flag(r, "mentioned")]
    domains = collections.Counter()
    for r in rows:
        for d in dict.fromkeys(normalize_domain(x) for x in r.get("cited_domains", []) if x):
            domains[d] += 1
    comp = {c: domains.get(c, 0) for c in competitors}
    by_lang = collections.defaultdict(lambda: {"questions": 0, "cited": 0, "good": 0})
    for r in rows:
        lang = "ar" if str(r.get("lang", "")).startswith("ar") else "en"
        by_lang[lang]["questions"] += 1
        by_lang[lang]["cited"] += flag(r, "cited")
        by_lang[lang]["good"] += r.get("answer_quality") == "good"
    quality = collections.Counter(r.get("answer_quality", "none") for r in rows)
    return {
        "questions": n,
        "client_cited": len(cited), "client_cited_pct": round(100 * len(cited) / n, 1) if n else 0,
        "client_mentioned": len(mentioned),
        "client_cited_ids": [r["id"] for r in cited],
        "top_domains": domains.most_common(25),
        "competitors": comp,
        "aggregator_share_pct": round(100 * sum(1 for r in rows if any(normalize_domain(d) in AGGREGATORS
                                                                       for d in r.get("cited_domains", []))) / n, 1) if n else 0,
        "by_lang": dict(by_lang),
        "quality": dict(quality),
        "weak_or_none_ids": [r["id"] for r in rows if r.get("answer_quality") in ("weak", "none")],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("round_json")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    domain = normalize_domain(a.client)
    folder = CLIENTS_DIR / domain
    c = load_json(folder / "client.json")
    competitors = [normalize_domain(x) for x in c.get("competitor_domains", [])]
    rows = sorted(json.load(open(a.round_json, encoding="utf-8")), key=lambda r: r.get("id", 0))
    today = dt.date.today().isoformat()

    prev_files = sorted(p for p in (folder / "data").glob("ai-visibility-*.json") if p.stem != f"ai-visibility-{today}")
    prev = score(load_json(prev_files[-1])["rows"], domain, competitors) if prev_files else None
    now = score(rows, domain, competitors)
    (folder / "data" / f"ai-visibility-{today}.json").write_text(
        json.dumps({"date": today, "score": now, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")

    def delta(key):
        return "" if not prev else f" (was {prev[key]})"

    L = [f"# {c.get('business_name') or domain}: AI search visibility", "",
         f"**Date:** {today} · **Questions sampled:** {now['questions']} · **Method:** one AI web search per customer question "
         "(free sample; not a full ChatGPT / Perplexity / AI Overviews tracker)", "",
         "## Scores", "", "| Measure | Value |", "|---|---|",
         f"| Questions where {domain} is cited as a source | **{now['client_cited']} of {now['questions']}** ({now['client_cited_pct']}%){delta('client_cited')} |",
         f"| Questions where the brand is named in the answer | {now['client_mentioned']}{delta('client_mentioned')} |",
         f"| Answers citing a big booking site / OTA | {now['aggregator_share_pct']}% of questions |",
         f"| Answer quality (good / weak / none) | {now['quality'].get('good', 0)} / {now['quality'].get('weak', 0)} / {now['quality'].get('none', 0)} |"]
    for lang, v in sorted(now["by_lang"].items()):
        L.append(f"| {'Arabic' if lang == 'ar' else 'English'} questions: cited / good answers | {v['cited']} / {v['good']} of {v['questions']} |")
    L += ["", "## Who AI search trusts (sources cited most often)", "", "| Source | Questions citing it |", "|---|---|"]
    L += [f"| {d} | {k} |" for d, k in now["top_domains"][:20]]
    if competitors:
        L += ["", "## Competitors", "", "| Competitor | Questions citing it |", "|---|---|"]
        L += [f"| {d} | {k}{'' if not prev else ' (was ' + str(prev['competitors'].get(d, 0)) + ')'} |" for d, k in now["competitors"].items()]
    L += ["", "## Question by question", "", "| # | Question | Cited? | Quality | Main sources | Answer in short |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['question']} | {'✅' if flag(r, 'cited') else '–'} | {r.get('answer_quality', '')} | "
                 f"{', '.join(dict.fromkeys(normalize_domain(d) for d in r.get('cited_domains', [])[:4]))} | {r.get('answer_gist', '')} |")
    out = folder / "reports" / f"ai-visibility-{today}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(out), **{k: now[k] for k in ("client_cited", "client_mentioned", "aggregator_share_pct", "quality", "by_lang", "competitors")},
                      "top_domains": now["top_domains"][:10]}, indent=2, ensure_ascii=False) if a.json else f"written {out}")


if __name__ == "__main__":
    main()
