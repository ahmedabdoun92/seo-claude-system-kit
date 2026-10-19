#!/usr/bin/env python3
"""Small polite crawler: indexing signals and internal links for every page in a sitemap.

Standard library only. For each URL it records: HTTP status, redirects, canonical,
meta robots + X-Robots-Tag, title, H1s, visible word count, and internal links out.
Then it counts internal links IN to every page (how well each page is linked).

Usage:
    python site_crawl.py https://www.example.com/sitemap.xml --json --save example.com
    python site_crawl.py https://www.example.com/sitemap.xml --follow   # also crawl linked pages not in the sitemap
"""

import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import CLIENTS_DIR, normalize_domain  # noqa: E402

UA = "Mozilla/5.0 (compatible; SEOClaudeSystem/1.0; site audit)"
SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.h1, self.text = [], [], []
        self.title = ""
        self.canonical = None
        self.robots = None
        self.lang = None
        self.hreflang = {}
        self.meta_description = None
        self._skip = 0
        self._in_title = self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "link" and "canonical" in (a.get("rel") or "").lower().split():
            self.canonical = a.get("href")
        elif tag == "link" and "alternate" in (a.get("rel") or "").lower().split() and a.get("hreflang"):
            self.hreflang[a["hreflang"]] = a.get("href")
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.meta_description = a.get("content") or ""
        elif tag == "meta" and (a.get("name") or "").lower() in ("robots", "googlebot"):
            self.robots = ((self.robots + ", ") if self.robots else "") + (a.get("content") or "")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
            self.h1.append("")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title += data
        if self._in_h1 and self.h1:
            self.h1[-1] += data
        self.text.append(data)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.geturl(), dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, dict(e.headers or {}), ""
    except Exception as e:  # network errors are data, not crashes
        return 0, url, {}, f"error: {e}"


def sitemap_urls(sitemap):
    _, _, _, body = fetch(sitemap)
    return [u.strip() for u in re.findall(r"<loc>([^<]+)</loc>", body)]


def norm(url):
    url = urldefrag(url)[0]
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path or '/'}"


def crawl(urls, host, follow, delay):
    pages, queue, seen = {}, list(urls), set()
    while queue:
        url = norm(queue.pop(0))
        if url in seen:
            continue
        seen.add(url)
        status, final, headers, body = fetch(url)
        p = PageParser()
        p.feed(body)
        internal = sorted({norm(urljoin(final, h)) for h in p.links
                           if urlparse(urljoin(final, h)).netloc == host
                           and not h.startswith(("mailto:", "tel:", "javascript:"))})
        words = len(re.findall(r"\w+", " ".join(p.text)))
        pages[url] = {
            "status": status, "final_url": final, "redirected": norm(final) != url,
            "canonical": p.canonical, "meta_robots": p.robots,
            "x_robots_tag": headers.get("X-Robots-Tag") or headers.get("x-robots-tag"),
            "title": p.title.strip(), "h1": [h.strip() for h in p.h1], "words": words,
            "lang": p.lang, "hreflang": p.hreflang, "meta_description": p.meta_description,
            "links_out": internal, "in_sitemap": url in urls,
        }
        if follow:
            queue += [u for u in internal if u not in seen]
        time.sleep(delay)
    for url, page in pages.items():
        page["links_in_from"] = sorted(u for u, other in pages.items() if u != url and url in other["links_out"])
        page["links_in"] = len(page["links_in_from"])
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sitemap")
    ap.add_argument("--follow", action="store_true", help="also crawl internal links not in the sitemap")
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--save", metavar="CLIENT")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    urls = [norm(u) for u in sitemap_urls(args.sitemap)]
    host = urlparse(args.sitemap).netloc
    pages = crawl(urls, host, args.follow, args.delay)
    report = {"date": datetime.date.today().isoformat(), "sitemap": args.sitemap, "pages": pages}
    if args.save:
        out = CLIENTS_DIR / normalize_domain(args.save) / "data" / f"crawl-{report['date']}.json"
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
        report["saved_to"] = str(out)
    if args.json:
        print(json.dumps(report, indent=1, ensure_ascii=False))
    else:
        for url, p in sorted(pages.items(), key=lambda kv: kv[1]["links_in"]):
            flags = [f for f, on in (("REDIRECT", p["redirected"]), ("NOINDEX", "noindex" in (p["meta_robots"] or "") + (p["x_robots_tag"] or "")),
                                     ("NOT-IN-SITEMAP", not p["in_sitemap"]), ("CANON-ELSEWHERE", p["canonical"] and norm(p["canonical"]) != url)) if on]
            print(f"{p['status']} in:{p['links_in']:>3} words:{p['words']:>5} {url} {' '.join(flags)}")


if __name__ == "__main__":
    main()
