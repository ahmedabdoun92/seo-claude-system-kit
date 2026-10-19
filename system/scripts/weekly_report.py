#!/usr/bin/env python3
"""Weekly SEO report for one client: rankings, decay alerts, indexing and conversions.

Compares the last complete week in Search Console (which runs ~3 days behind) with the
week before, re-checks every sitemap URL in Google's index, counts GA4 conversion events,
saves snapshots for next time and writes a Markdown report into the client folder.

Usage:
    python weekly_report.py example.com
    python weekly_report.py example.com --no-inspect      # skip URL Inspection (faster)
    python weekly_report.py example.com --min-impr 5       # ignore queries below 5 impressions

client.json fields used: gsc_property, ga4_property_id, canonical_host,
conversion_events (optional, list of GA4 event names).
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CLIENTS_DIR, load_json, normalize_domain, run_seo_script  # noqa: E402

DEFAULT_EVENTS = ["generate_lead", "whatsapp_click", "phone_click", "email_click", "messenger_click", "trip_form_error"]
VENV_PY = Path(os.path.expanduser("~/.claude/skills/seo/.venv")) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
GA4_EVENTS = Path(__file__).resolve().parent / "ga4_events.py"


# ------------------------------------------------------------------ data pulls

def gsc(prop, start, end, dims):
    code, out = run_seo_script("gsc_query.py", "--property", prop, "--start-date", start, "--end-date", end,
                               "--dimensions", dims, "--limit", "5000", "--json", timeout=300)
    if not isinstance(out, dict) or out.get("error"):
        raise RuntimeError(f"Search Console ({dims}): {out.get('error') if isinstance(out, dict) else out}")
    return out


def rows_by(out, key):
    return {r[key]: {"clicks": r["clicks"], "impressions": r["impressions"], "position": r["position"]}
            for r in out.get("rows", [])}


def ga4_events(prop, start, end, events, host):
    if not VENV_PY.exists():
        return {"error": "claude-seo .venv not found"}
    args = [str(VENV_PY), str(GA4_EVENTS), "--property", prop, "--start", start, "--end", end,
            "--events", ",".join(events)]
    if host:
        args += ["--host", host]
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"error": (p.stderr or p.stdout)[-300:]}


def sitemap_urls(host):
    req = urllib.request.Request(f"https://{host}/sitemap.xml", headers={"User-Agent": "SEOClaudeSystem/1.0"})
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    return re.findall(r"<loc>([^<]+)</loc>", body)


def inspect_all(prop, urls, folder):
    batch = folder / "data" / "_inspect-batch.txt"
    batch.write_text("\n".join(urls), encoding="utf-8")
    try:  # URL Inspection takes ~5 s per URL
        code, out = run_seo_script("gsc_inspect.py", "--batch", str(batch), "--site-url", prop, "--delay", "0.5",
                                   "--json", timeout=120 + 12 * len(urls))
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"URL Inspection timed out for {len(urls)} URLs; run again or use --no-inspect")
    finally:
        batch.unlink(missing_ok=True)
    rows = out.get("results", out) if isinstance(out, dict) else out
    if not isinstance(rows, list):
        raise RuntimeError(f"URL Inspection: {str(out)[:200]}")
    return {r["url"]: (r.get("index_status") or {}).get("coverage_state") or "unknown" for r in rows}


# ------------------------------------------------------------------ comparison helpers

def bing_week(site, start, end):
    """Bing Webmaster clicks/impressions for the week and the latest crawl stats (free API key from setup_keys.py)."""
    try:
        cfg = Path.home() / ".config" / "claude-seo" / "backlinks-api.json"
        key = (json.loads(cfg.read_text()) if cfg.exists() else {}).get("bing_api_key") or os.environ.get("BING_WEBMASTER_API_KEY")
        if not key or not site:
            return {"error": "no Bing key or bing_site in client.json"}
        base = "https://ssl.bing.com/webmaster/api.svc/json/"
        q = f"?siteUrl={urllib.parse.quote(site, safe='')}&apikey={key}"
        def get(method):
            with urllib.request.urlopen(base + method + q, timeout=30) as r:
                return json.loads(r.read()).get("d") or []
        def day(v):  # "/Date(1729123200000)/" -> date
            ms = int(re.search(r"\d+", v).group(0))
            return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date()
        traffic = [r for r in get("GetRankAndTrafficStats") if start <= day(r["Date"]) <= end]
        crawl = get("GetCrawlStats")
        last = crawl[-1] if crawl else {}
        return {"clicks": sum(r.get("Clicks", 0) for r in traffic), "impressions": sum(r.get("Impressions", 0) for r in traffic),
                "days": len(traffic), "in_index": last.get("InIndex"), "crawled": last.get("CrawledPages"),
                "crawl_errors": last.get("CrawlErrors")}
    except Exception as e:
        return {"error": str(e)[:200]}


def pct(new, old):
    if not old:
        return "new" if new else "–"
    return f"{(new - old) / old * 100:+.0f}%"


def latest_snapshot(folder, pattern, before_name=None):
    files = sorted(p for p in (folder / "snapshots").glob(pattern) if p.name != before_name)
    return load_json(files[-1]) if files else None


def short(url, host):
    return url.replace(f"https://{host}", "") or "/"


# ------------------------------------------------------------------ report

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("--no-inspect", action="store_true")
    ap.add_argument("--min-impr", type=int, default=3, help="minimum impressions for a query to count as ranked")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    domain = normalize_domain(a.client)
    folder = CLIENTS_DIR / domain
    c = load_json(folder / "client.json")
    if not c.get("gsc_property"):
        sys.exit(f"No gsc_property in {folder / 'client.json'}")
    host = normalize_domain(c.get("canonical_host") or domain)
    host = ("www." + host) if c.get("canonical_host", "").startswith("https://www.") else host
    events = c.get("conversion_events") or DEFAULT_EVENTS

    today = dt.date.today()
    end = today - dt.timedelta(days=3)
    this_w = ((end - dt.timedelta(days=6)).isoformat(), end.isoformat())
    prev_w = ((end - dt.timedelta(days=13)).isoformat(), (end - dt.timedelta(days=7)).isoformat())
    print(f"[weekly] {domain}: this week {this_w[0]}..{this_w[1]} vs {prev_w[0]}..{prev_w[1]}")

    # Search Console
    q_now, q_prev = gsc(c["gsc_property"], *this_w, "query"), gsc(c["gsc_property"], *prev_w, "query")
    p_now, p_prev = gsc(c["gsc_property"], *this_w, "page"), gsc(c["gsc_property"], *prev_w, "page")
    tot_now, tot_prev = q_now.get("totals") or {}, q_prev.get("totals") or {}
    qn, qp = rows_by(q_now, "query"), rows_by(q_prev, "query")
    pn, pp = rows_by(p_now, "page"), rows_by(p_prev, "page")

    movers = []
    for q in set(qn) & set(qp):
        if qn[q]["impressions"] >= a.min_impr and qp[q]["impressions"] >= a.min_impr:
            movers.append((q, qp[q]["position"], qn[q]["position"], qn[q]["impressions"]))
    up = sorted([m for m in movers if m[2] < m[1] - 0.5], key=lambda m: m[2] - m[1])[:10]
    down = sorted([m for m in movers if m[2] > m[1] + 0.5], key=lambda m: m[1] - m[2])[:10]
    new_q = sorted([(q, v) for q, v in qn.items() if q not in qp and v["impressions"] >= a.min_impr],
                   key=lambda x: -x[1]["impressions"])[:15]
    lost_q = sorted([(q, v) for q, v in qp.items() if q not in qn and v["impressions"] >= a.min_impr],
                    key=lambda x: -x[1]["impressions"])[:10]
    quick_wins = sorted([(q, v) for q, v in qn.items() if 4 <= v["position"] <= 15 and v["impressions"] >= a.min_impr],
                        key=lambda x: -x[1]["impressions"])[:10]

    decay = []
    for page, old in pp.items():
        new = pn.get(page, {"clicks": 0, "impressions": 0, "position": 0})
        if old["impressions"] >= 10 and new["impressions"] < old["impressions"] * 0.7:
            decay.append((page, old, new))
        elif old["clicks"] >= 3 and new["clicks"] < old["clicks"] * 0.5:
            decay.append((page, old, new))
    decay.sort(key=lambda d: d[2]["impressions"] - d[1]["impressions"])

    # Index status
    index_now, index_prev, newly, dropped, not_indexed, index_error = {}, {}, [], [], [], None
    if not a.no_inspect:
        prev_snap = latest_snapshot(folder, "index-*.json") or latest_snapshot(folder, "gsc-2*.json") or {}
        index_prev = prev_snap.get("index", {})
        print("[weekly] checking every sitemap URL in Google (about 5 s each)...")
        try:
            index_now = inspect_all(c["gsc_property"], sitemap_urls(host), folder)
        except Exception as exc:  # keep the rest of the report
            index_error = str(exc)
        newly = [u for u, s in index_now.items() if s == "Submitted and indexed" and index_prev.get(u) != "Submitted and indexed"]
        dropped = [u for u, s in index_now.items() if s != "Submitted and indexed" and index_prev.get(u) == "Submitted and indexed"]
        not_indexed = [(u, s) for u, s in index_now.items() if s != "Submitted and indexed"]

    # GA4
    ga_now = ga_prev = {}
    if c.get("ga4_property_id"):
        ga_now = ga4_events(c["ga4_property_id"], *this_w, events, host)
        ga_prev = ga4_events(c["ga4_property_id"], *prev_w, events, host)

    # Snapshots for next week
    (folder / "snapshots").mkdir(exist_ok=True)
    snap = {"date": today.isoformat(), "window": f"{this_w[0]}..{this_w[1]}", "totals": tot_now,
            "queries": [{"query": k, **v} for k, v in qn.items()], "pages": [{"page": k, **v} for k, v in pn.items()]}
    (folder / "snapshots" / f"gsc-week-{this_w[1]}.json").write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
    if index_now:
        (folder / "snapshots" / f"index-{today.isoformat()}.json").write_text(
            json.dumps({"date": today.isoformat(), "index": index_now}, indent=1), encoding="utf-8")

    # Markdown
    L = [f"# {c.get('business_name') or domain}: weekly SEO report", "",
         f"**Report date:** {today} · **This week:** {this_w[0]} → {this_w[1]} · **Previous week:** {prev_w[0]} → {prev_w[1]}",
         "Search Console data runs about 3 days behind, so \"this week\" ends 3 days ago. Small numbers swing a lot; read the counts, not just the %.", "",
         "## Summary", "", "| | This week | Previous week | Change |", "|---|---|---|---|"]
    for k, label in (("clicks", "Google clicks"), ("impressions", "Google impressions")):
        L.append(f"| {label} | {tot_now.get(k, 0)} | {tot_prev.get(k, 0)} | {pct(tot_now.get(k, 0), tot_prev.get(k, 0))} |")
    L.append(f"| Average position | {tot_now.get('position', '–')} | {tot_prev.get('position', '–')} | |")
    if ga_now and not ga_now.get("error"):
        conv_now = sum(v for k, v in ga_now["events"].items() if k != "trip_form_error")
        conv_prev = sum(v for k, v in (ga_prev.get("events") or {}).items() if k != "trip_form_error")
        L.append(f"| Conversions (contact clicks + leads) | {conv_now} | {conv_prev} | {pct(conv_now, conv_prev)} |")
        org_now = next((x["sessions"] for x in ga_now["channels"] if x["channel"] == "Organic Search"), 0)
        org_prev = next((x["sessions"] for x in ga_prev.get("channels", []) if x["channel"] == "Organic Search"), 0)
        L.append(f"| Sessions from Google (GA4) | {org_now} | {org_prev} | {pct(org_now, org_prev)} |")
    if index_now:
        L.append(f"| Pages indexed | {sum(1 for s in index_now.values() if s == 'Submitted and indexed')} of {len(index_now)} | "
                 f"{sum(1 for s in index_prev.values() if s == 'Submitted and indexed')} of {len(index_prev) or '–'} | |")

    L += ["", "## Rankings", ""]
    if up or down:
        L += ["| Search | Was | Now | Impressions |", "|---|---|---|---|"]
        L += [f"| ⬆ {q} | {p0:.1f} | {p1:.1f} | {im} |" for q, p0, p1, im in up]
        L += [f"| ⬇ {q} | {p0:.1f} | {p1:.1f} | {im} |" for q, p0, p1, im in down]
    else:
        L.append(f"No search with at least {a.min_impr} impressions in both weeks moved by more than half a position.")
    if new_q:
        L += ["", "**New searches showing the site:** " + ", ".join(f"{q} ({v['impressions']} impr., pos {v['position']:.0f})" for q, v in new_q)]
    if lost_q:
        L += ["", "**Searches that stopped showing the site:** " + ", ".join(f"{q} (had {v['impressions']} impr.)" for q, v in lost_q)]
    if quick_wins:
        L += ["", "**Quick wins** (position 4–15, improve the page to reach the top 3):", ""]
        L += [f"- {q}: position {v['position']:.1f}, {v['impressions']} impressions" for q, v in quick_wins]

    L += ["", "## Decay alerts", ""]
    if decay:
        L += ["| Page | Impressions (prev → now) | Clicks (prev → now) |", "|---|---|---|"]
        L += [f"| {short(pg, host)} | {o['impressions']} → {n['impressions']} | {o['clicks']} → {n['clicks']} |" for pg, o, n in decay[:15]]
    else:
        L.append("No page lost 30% or more of its impressions (from at least 10) or half its clicks (from at least 3).")

    if index_error:
        L += ["", "## Indexing", "", f"Not checked this time: {index_error}"]
    if index_now:
        L += ["", "## Indexing", ""]
        if newly:
            L += ["**Newly indexed:** " + ", ".join(short(u, host) for u in newly)]
        if dropped:
            L += ["", "**⚠ Dropped out of the index:** " + ", ".join(short(u, host) for u in dropped)]
        if not_indexed:
            L += ["", f"**Not indexed yet ({len(not_indexed)}):**", ""]
            L += [f"- {short(u, host)}: {s}" for u, s in sorted(not_indexed, key=lambda x: x[1])]

    if ga_now and not ga_now.get("error"):
        L += ["", "## Conversions (GA4, live site only)", "", "| Event | This week | Previous week |", "|---|---|---|"]
        L += [f"| {e} | {ga_now['events'].get(e, 0)} | {(ga_prev.get('events') or {}).get(e, 0)} |" for e in events]
        top = sorted(ga_now["by_page"], key=lambda r: -r["count"])[:10]
        if top:
            L += ["", "**Where they happened:** " + ", ".join(f"{r['page']} ({r['event']} ×{r['count']})" for r in top)]
        if ga_now["events"].get("trip_form_error"):
            L += ["", f"⚠ **The trip form failed {ga_now['events']['trip_form_error']} time(s) this week.** Check Supabase and the form."]
    elif ga_now.get("error"):
        L += ["", f"## Conversions", "", f"GA4 error: {ga_now['error']}"]

    bing = bing_week(c.get("bing_site"), dt.date.fromisoformat(this_w[0]), dt.date.fromisoformat(this_w[1]))
    L += ["", "## Bing (Bing also feeds ChatGPT search)", ""]
    if bing.get("error"):
        L.append(f"Not available: {bing['error']}")
    elif not bing["days"] and not bing["crawled"]:
        L.append("No Bing data yet for this site (verified, but Bing has not reported crawling or impressions). Switching on IndexNow speeds this up.")
    else:
        L += [f"- Clicks: {bing['clicks']} · Impressions: {bing['impressions']} ({bing['days']} days with data)",
              f"- Pages in Bing's index: {bing['in_index'] if bing['in_index'] is not None else '–'} · crawled: {bing['crawled'] if bing['crawled'] is not None else '–'} · crawl errors: {bing['crawl_errors'] if bing['crawl_errors'] is not None else '–'}"]

    def priority(u):  # money pages first; legal pages last
        p = short(u, host)
        if re.search(r"/(privacy|terms|cookies?)/", p):
            return 9
        return next((i for i, part in enumerate(("/hotels/", "/destinations/", "/blog/")) if p.startswith(part) and p != part), 5)

    todo = []
    if not_indexed:
        try:  # skip URLs requested in the last 14 days (indexing_queue.py --mark records them)
            from indexing_queue import queue as indexing_queue
            ranked = indexing_queue(domain, 10).get("today") or []
        except Exception:
            ranked = sorted((u for u, _ in not_indexed), key=priority)[:10]
        if ranked:
            todo.append("Request indexing in Search Console for these (about 10 a day, money pages first; "
                        f"`python system/scripts/indexing_queue.py {domain} --mark` records them): "
                        + ", ".join(short(u, host) for u in ranked[:10]))
    if decay:
        todo.append("Refresh the pages in Decay alerts: update facts, add sections, check their titles.")
    if quick_wins:
        todo.append("Improve the pages behind the Quick wins: better title and H1 for that search, more detail, internal links.")
    if dropped:
        todo.append("Inspect the pages that dropped out of the index (URL Inspection) and fix what Google reports.")
    L += ["", "## What to do this week", ""] + ([f"{i}. {t}" for i, t in enumerate(todo, 1)] or ["Nothing urgent. Keep publishing and requesting indexing."])

    todo_file = folder / "todo.md"
    if todo_file.exists():
        text = todo_file.read_text(encoding="utf-8")
        for section, label in (("Owner", "Waiting on the owner"), ("Waiting", "Blocked / waiting")):
            m = re.search(rf"^## {section}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
            items = re.findall(r"^- \[ \] (.+)$", m.group(1), re.M) if m else []
            if items:
                L += ["", f"## {label} (from todo.md)", ""] + [f"- {i}" for i in items]

    report = folder / "reports" / f"weekly-{today.isoformat()}.md"
    report.write_text("\n".join(L) + "\n", encoding="utf-8")

    log = folder / "log.md"
    if log.exists():
        lines = log.read_text(encoding="utf-8").splitlines()
        entry = (f"- {today} · Reporting · Weekly report: {tot_now.get('clicks', 0)} clicks / {tot_now.get('impressions', 0)} impressions "
                 f"(prev {tot_prev.get('clicks', 0)} / {tot_prev.get('impressions', 0)})"
                 + (f", {sum(1 for s in index_now.values() if s == 'Submitted and indexed')}/{len(index_now)} indexed" if index_now else "")
                 + f" · `reports/{report.name}`")
        idx = next((i for i, l in enumerate(lines) if l.startswith("- ")), len(lines))
        lines.insert(idx, entry)
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {"report": str(report), "totals_now": tot_now, "totals_prev": tot_prev, "movers_up": len(up),
               "movers_down": len(down), "new_queries": len(new_q), "decay": len(decay), "newly_indexed": len(newly),
               "dropped": len(dropped), "not_indexed": len(not_indexed),
               "conversions": ga_now.get("events") if ga_now and not ga_now.get("error") else None}
    print(json.dumps(summary, indent=2, ensure_ascii=False) if a.json else f"[weekly] report written: {report}")


if __name__ == "__main__":
    main()
