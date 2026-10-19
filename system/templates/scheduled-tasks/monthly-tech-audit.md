Monthly technical SEO check for the client {{DOMAIN}} in the SEO Claude System (home folder {{HOME_SCS}}). Follow the house rules in {{HOME_SCS}}/CLAUDE.md (free tools only; do not change the client's website or push anything).

1. Run: python "{{HOME_SCS}}/system/scripts/tech_audit.py" {{DOMAIN}}
   (3–5 minutes: crawls every sitemap URL of {{SITE_URL}} and checks status codes, canonicals, titles, descriptions, H1s, thin and weakly linked pages, broken links, language pairs, robots.txt / sitemap / llms.txt, crawler access, the lead-path URLs in client.json monitor_urls, and mobile PageSpeed.) It writes reports/tech-audit-<date>.md, data/tech-audit-<date>.json and a log line.
2. Reply in plain words: pages checked, how many OK, problems, new vs fixed since last month. List new problems first (page, problem, fix) and say who does each fix: website code (Claude on a branch, when asked) or the owner (CMS admin, DNS/CDN, Search Console). A single PageSpeed score of 85–90 is normal lab variance. If all is clean, say so in one sentence.
3. Do not fix anything automatically. End with the report path.
