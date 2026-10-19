#!/usr/bin/env python3
"""Monthly technical SEO check of a client's live site (free tools only).

Crawls every URL in the sitemap (site_crawl.py) and flags, each with the fix:
  - pages that do not return 200, redirect, or have a canonical pointing elsewhere
  - noindex pages listed in the sitemap
  - missing / duplicate / too long titles, missing or odd-length meta descriptions, H1 count != 1
  - thin pages (under 300 words), pages with no internal links, and pages with fewer than 3 links
    from other pages' content (link_map.py: menus and footers not counted)
  - internal links that point to pages that do not return 200
  - hreflang pairs that are not reciprocal or point to broken pages, and <html lang> that does not
    match the URL language (/ar/ = Arabic)
  - robots.txt, sitemap and llms.txt reachable; AI and search crawlers allowed (HTTP 200)
  - lead path: every client.json "monitor_urls" entry answers with its expected status (forms, publish hooks)
  - mobile PageSpeed (score, LCP, CLS) for the home page and one hotel page in each language
It compares with the previous run (new problems / fixed problems), saves data/tech-audit-<date>.json,
writes reports/tech-audit-<date>.md and adds a line to log.md.

Usage:
    python tech_audit.py example.com            # full run (PageSpeed adds ~2 minutes)
    python tech_audit.py example.com --no-psi   # skip PageSpeed
"""

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CLIENTS_DIR, load_json, normalize_domain, run_seo_script  # noqa: E402
from site_crawl import crawl, norm, sitemap_urls  # noqa: E402
from link_map import build_map  # noqa: E402

BOTS = {
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "OAI-SearchBot": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "GPTBot": "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)",
    "ClaudeBot": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
}


def status_of(url: str, ua: str = "Mozilla/5.0 (compatible; SEOClaudeSystem/1.0)", method: str = "GET") -> int:
    req = urllib.request.Request(url, headers={"User-Agent": ua}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def psi(url: str) -> dict:
    code, out = run_seo_script("pagespeed_check.py", url, "--strategy", "mobile", "--psi-only", "--json", timeout=240)
    try:
        m = out["psi"]["mobile"]
        lab = m["lab_metrics"]
        return {"score": m["lighthouse_scores"]["performance"],
                "lcp": lab["largest-contentful-paint"]["display"].replace("\xa0", " "),
                "cls": lab["cumulative-layout-shift"]["display"]}
    except Exception:
        return {"error": str(out)[:200]}


def audit_pages(pages: dict, base: str) -> list[dict]:
    """One issue = {key, page, problem, fix}. `key` is stable so runs can be compared."""
    issues = []

    def add(page, kind, problem, fix):
        issues.append({"key": f"{kind}|{page}", "kind": kind, "page": page.replace(base, "") or "/", "problem": problem, "fix": fix})

    titles = Counter(p["title"] for p in pages.values() if p["status"] == 200)
    for url, p in pages.items():
        path = url.replace(base, "") or "/"
        if p["status"] != 200:
            add(url, "status", f"returns HTTP {p['status']}", "Fix or remove the page; take it out of the sitemap if it should not exist.")
            continue
        if p["redirected"]:
            add(url, "redirect", f"redirects to {p['final_url']}", "List the final URL in the sitemap and in internal links.")
        if p["canonical"] and norm(p["canonical"]) != url:
            add(url, "canonical", f"canonical points to {p['canonical']}", "Make the canonical point to the page itself, or drop the page from the sitemap.")
        robots = ((p.get("meta_robots") or "") + " " + (p.get("x_robots_tag") or "")).lower()
        if "noindex" in robots and p.get("in_sitemap"):
            add(url, "noindex", "is noindex but listed in the sitemap", "Remove it from the sitemap, or remove the noindex.")
        if not p["title"]:
            add(url, "title", "has no <title>", "Add a unique title (20–70 characters).")
        elif titles[p["title"]] > 1:
            add(url, "title-dup", f"shares its title with {titles[p['title']] - 1} other page(s)", "Give each page a unique title.")
        elif len(p["title"]) > 70:
            add(url, "title-long", f"title is {len(p['title'])} characters", "Shorten the title to 70 characters or fewer.")
        md = p.get("meta_description")
        if md is None or not md.strip():
            add(url, "description", "has no meta description", "Add a meta description (70–165 characters).")
        elif not 50 <= len(md) <= 175:
            add(url, "description-length", f"meta description is {len(md)} characters", "Keep meta descriptions between 70 and 165 characters.")
        if len(p["h1"]) != 1:
            add(url, "h1", f"has {len(p['h1'])} H1 headings", "Use exactly one H1 per page.")
        if p["words"] < 300 and path not in ("/contact/", "/ar/contact/"):
            add(url, "thin", f"only {p['words']} words", "Add useful, specific content or merge the page into a stronger one.")
        if p["links_in"] == 0:
            add(url, "orphan", "no internal links point to it", "Link to it from related hotel, destination or guide pages.")
        want = "ar" if path.startswith("/ar/") else "en"
        if (p.get("lang") or "").split("-")[0] != want:
            add(url, "lang", f"<html lang=\"{p.get('lang')}\"> on a {want} page", f"Set <html lang=\"{want}\">.")
        for hl, href in (p.get("hreflang") or {}).items():
            target = norm(href) if href else None
            if target and target in pages:
                if pages[target]["status"] != 200:
                    add(url, f"hreflang-broken-{hl}", f"hreflang {hl} points to a page returning {pages[target]['status']}", "Point hreflang only at live pages.")
                elif hl != "x-default" and url not in [norm(h) for h in (pages[target].get("hreflang") or {}).values() if h]:
                    add(url, f"hreflang-return-{hl}", f"hreflang {hl} → {href} does not link back", "Make every hreflang pair point at each other.")
    # internal links to pages that were not crawled (not in the sitemap): check they are live
    crawled = set(pages)
    extra = sorted({l for p in pages.values() for l in p["links_out"] if l not in crawled and l.startswith(base)})
    for link in extra:
        code = status_of(link)
        if code != 200:
            sources = [u.replace(base, "") or "/" for u, p in pages.items() if link in p["links_out"]][:5]
            add(link, "broken-link", f"linked from {', '.join(sources)} but returns HTTP {code}", "Fix the link or add a redirect.")
    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("--no-psi", action="store_true")
    ap.add_argument("--delay", type=float, default=0.3)
    a = ap.parse_args()

    domain = normalize_domain(a.client)
    folder = CLIENTS_DIR / domain
    c = load_json(folder / "client.json")
    base = (c.get("canonical_host") or f"https://{domain}").rstrip("/")
    today = dt.date.today().isoformat()

    urls = [norm(u) for u in sitemap_urls(f"{base}/sitemap.xml")]
    pages = crawl(urls, base.split("://")[1], follow=False, delay=a.delay)
    issues = audit_pages(pages, base)
    links = build_map(base, urls)
    for u in links["weak"]:
        n = links["pages"][u]["links_in"]
        issues.append({"key": f"weak-links|{u}", "kind": "weak-links", "page": u.replace(base, "") or "/",
                       "problem": f"only {n} link(s) from other pages' content (menus and footers not counted)",
                       "fix": "Link to it from related hotel, destination or guide pages."})

    site_checks = {name: status_of(f"{base}{path}") for name, path in
                   [("robots.txt", "/robots.txt"), ("sitemap.xml", "/sitemap.xml"), ("llms.txt", "/llms.txt")]}
    bots = {name: status_of(f"{base}/", ua) for name, ua in BOTS.items()}
    # Lead path: forms, publish hooks, booking links (client.json "monitor_urls": [{name, url, method, expect}])
    monitors = {}
    for m in c.get("monitor_urls", []):
        code = status_of(m["url"], method=m.get("method", "GET"))
        monitors[m["name"]] = code
        if code not in m.get("expect", [200]):
            issues.append({"key": f"monitor|{m['name']}", "kind": "lead-path", "page": m["name"],
                           "problem": f"answered HTTP {code} (expected {', '.join(map(str, m.get('expect', [200])))})",
                           "fix": "Check the function or service behind it (Supabase functions, form endpoint, booking link) before customers notice."})
    for name, code in {**site_checks, **bots}.items():
        if code != 200:
            issues.append({"key": f"site|{name}", "kind": "site", "page": name, "problem": f"returns HTTP {code}",
                           "fix": "Check Cloudflare AI Crawl Control / robots rules and the file itself."})

    speed = {}
    if not a.no_psi:
        hotel = next((u for u in urls if "/hotels/" in u and u.count("/") > 4 and "/ar/" not in u), None)
        samples = [f"{base}/", f"{base}/ar/"] + ([hotel, hotel.replace(base, base + "/ar")] if hotel else [])
        for u in samples:
            speed[u.replace(base, "") or "/"] = psi(u)
        for page, s in speed.items():
            if "score" in s and s["score"] < 85:  # lab scores swing about ±10 between runs
                issues.append({"key": f"speed|{page}", "kind": "speed", "page": page, "problem": f"mobile PageSpeed {s['score']} (LCP {s['lcp']}, CLS {s['cls']})",
                               "fix": "Check the largest image and the JavaScript size on this page."})

    prev_files = sorted(p for p in (folder / "data").glob("tech-audit-*.json") if p.stem != f"tech-audit-{today}")
    prev_keys = {i["key"] for i in load_json(prev_files[-1]).get("issues", [])} if prev_files else None
    now_keys = {i["key"] for i in issues}
    new = [i for i in issues if prev_keys is not None and i["key"] not in prev_keys]
    fixed = sorted(prev_keys - now_keys) if prev_keys is not None else []

    (folder / "data" / f"tech-audit-{today}.json").write_text(json.dumps(
        {"date": today, "pages": len(pages), "issues": issues, "site_checks": site_checks, "bots": bots, "monitors": monitors, "speed": speed},
        indent=1, ensure_ascii=False), encoding="utf-8")

    by_kind = Counter(i["kind"].split("-")[0] for i in issues)
    ok200 = sum(1 for p in pages.values() if p["status"] == 200)
    L = [f"# {c.get('business_name') or domain}: monthly technical check", "",
         f"**Date:** {today} · **Pages in sitemap:** {len(urls)} · **Returning 200:** {ok200} · **Problems found:** {len(issues)}"
         + (f" ({len(new)} new, {len(fixed)} fixed since {prev_files[-1].stem.replace('tech-audit-', '')})" if prev_keys is not None else " (first run)"), "",
         "## Site files and crawler access", "", "| Check | HTTP |", "|---|---|"]
    L += [f"| {k} | {v}{'' if v == 200 else ' ⚠'} |" for k, v in {**site_checks, **bots}.items()]
    if monitors:
        expect = {m["name"]: m.get("expect", [200]) for m in c.get("monitor_urls", [])}
        L += ["", "## Lead path (forms, publish, booking links)", "", "| Check | HTTP |", "|---|---|"]
        L += [f"| {k} | {v}{'' if v in expect[k] else ' ⚠'} |" for k, v in monitors.items()]
    if speed:
        L += ["", "## Mobile PageSpeed (Google lab test)", "", "| Page | Score | LCP | CLS |", "|---|---|---|---|"]
        L += [f"| {p} | {s.get('score', '?')} | {s.get('lcp', '?')} | {s.get('cls', '?')} |" for p, s in speed.items()]
    L += ["", "## Problems", ""]
    if not issues:
        L.append("None. Every sitemap page returns 200 with a self-canonical, one H1, a title, a description, a correct language tag and working hreflang.")
    else:
        L += ["| Type | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in by_kind.most_common()] + ["", "| Page | Problem | Fix |", "|---|---|---|"]
        L += [f"| {i['page']} | {i['problem']}{' 🆕' if i in new else ''} | {i['fix']} |" for i in issues[:150]]
        if len(issues) > 150:
            L.append(f"\n…and {len(issues) - 150} more in data/tech-audit-{today}.json")
    if fixed:
        L += ["", "## Fixed since last run", ""] + [f"- {k.split('|', 1)[1]} ({k.split('|', 1)[0]})" for k in fixed[:50]]
    report = folder / "reports" / f"tech-audit-{today}.md"
    report.write_text("\n".join(L) + "\n", encoding="utf-8")

    log = folder / "log.md"
    if log.exists():
        lines = log.read_text(encoding="utf-8").splitlines()
        idx = next((i for i, l in enumerate(lines) if l.startswith("- ")), len(lines))
        lines.insert(idx, f"- {today} · Technical · Monthly technical check: {len(urls)} pages, {ok200} OK, {len(issues)} problems"
                     + (f" ({len(new)} new, {len(fixed)} fixed)" if prev_keys is not None else "") + f" · `reports/{report.name}`")
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"report": str(report), "pages": len(urls), "ok": ok200, "issues": len(issues), "by_kind": dict(by_kind),
                      "new": len(new), "fixed": len(fixed), "bots": bots, "speed": speed}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
