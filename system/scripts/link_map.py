#!/usr/bin/env python3
"""Internal link map from page content: which pages link to which, counting only links inside <main>.

Menu and footer links appear on every page, so they hide weak spots. This map ignores them and shows
how many *content* links point at each page (hotel cards, guide lists, in-text links). A page with
fewer than 3 is weakly linked: Google finds and ranks it more slowly.

Usage:
    python link_map.py example.com            # live site, from its sitemap; saves data/link-map-<date>.json
    python link_map.py example.com --json     # print the full map
Used by tech_audit.py (weak-links check).
"""

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CLIENTS_DIR, load_json, normalize_domain  # noqa: E402
from site_crawl import norm, sitemap_urls  # noqa: E402

UA = "Mozilla/5.0 (compatible; SEOClaudeSystem/1.0; link map)"
# Pages that only need menu/footer links
EXEMPT = ("/privacy/", "/terms/", "/contact/")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def content_links(html: str, page_url: str, host: str) -> set[str]:
    m = re.search(r"<main\b.*?</main>", html, re.S | re.I)
    body = m.group(0) if m else re.sub(r"<(header|footer|nav)\b.*?</\1>", "", html, flags=re.S | re.I)
    out = set()
    for href in re.findall(r'href="([^"#]+)', body):
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(page_url, href)
        if urlparse(full).netloc == host and not re.search(r"\.\w{2,4}$", urlparse(full).path):
            out.add(norm(full.split("?")[0]))
    return out


def build_map(base: str, urls: list[str], delay: float = 0.2) -> dict:
    host = urlparse(base).netloc
    links = {}
    for u in urls:
        try:
            links[u] = sorted(content_links(fetch(u), u, host) - {u})
        except Exception as e:  # unreachable pages are the crawl check's job
            links[u] = []
            print(f"[link-map] could not fetch {u}: {e}", file=sys.stderr)
        time.sleep(delay)
    inbound = {u: sorted(src for src, outs in links.items() if u in outs) for u in urls}
    pages = {u: {"links_in": len(inbound[u]), "links_in_from": inbound[u], "links_out": len(links[u])} for u in urls}
    weak = sorted((u for u in urls if pages[u]["links_in"] < 3 and not u.endswith(EXEMPT)), key=lambda u: pages[u]["links_in"])
    return {"pages": pages, "weak": weak}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    domain = normalize_domain(a.client)
    folder = CLIENTS_DIR / domain
    c = load_json(folder / "client.json")
    base = (c.get("canonical_host") or f"https://{domain}").rstrip("/")
    urls = [norm(u) for u in sitemap_urls(f"{base}/sitemap.xml")]
    result = build_map(base, urls)
    out = folder / "data" / f"link-map-{dt.date.today().isoformat()}.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        print(f"{len(urls)} pages; weakly linked (fewer than 3 content links): {len(result['weak'])}")
        for u in result["weak"]:
            print(f"  {result['pages'][u]['links_in']}  {u.replace(base, '') or '/'}")
        print(f"saved {out}")


if __name__ == "__main__":
    main()
