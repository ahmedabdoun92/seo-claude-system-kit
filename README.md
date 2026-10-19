# SEO Claude System

**A complete SEO department for any website, run by [Claude Code](https://claude.com/claude-code) on free data.**

10 departments, 50 roles, weekly and monthly loops, and reports in English or Arabic. It finds problems, fixes them through changes you review, and checks that each fix worked, using Google's and Bing's own free data. No SEO tool subscriptions.

> Overview page: [`docs/index.html`](docs/index.html) (open it in a browser).

---

## What you get

| | |
|---|---|
| **Onboarding** | Asks for the business facts (never guesses), finds the 3–5 biggest competitors with free authority numbers, drafts 20–50 real customer questions. |
| **Technical SEO** | A monthly live check of every sitemap URL: status codes, canonicals, titles, descriptions, H1s, thin and weakly linked pages, broken links, hreflang pairs, robots.txt / sitemap / llms.txt, AI and search crawler access, forms and booking links, mobile PageSpeed. Compared with last month. |
| **Weekly report** | Clicks, impressions, rankings and movers, new and lost searches, decaying pages, the index status of every URL, Bing, GA4 conversions, and a ranked "what to do this week" list. |
| **AI search visibility** | Every customer question asked to AI web search each month: who gets cited, whether the client is named, which sources AI trusts, and which pages to build. |
| **Content** | Briefs, answer-first guides and comparison pages from sourced fact sheets, in every language the business serves, with internal links. |
| **Client report** | A branded monthly HTML report for the client, in English or Arabic, with every number sourced. |
| **Operations** | A to-do list per client (owner / Claude / waiting), an all-clients overview, an indexing queue (10 URLs a day, money pages first), backups, a setup checker and a self-test. |

The full role list, with honest **ready / partial / planned** status, is in [`system/reference/departments.md`](system/reference/departments.md). Today: 34 ready, 10 partial, 6 planned.

## Requirements

- [Claude Code](https://claude.com/claude-code) (CLI or desktop app; the desktop app adds scheduled tasks)
- Python 3.10+ and Git (on Windows, Git for Windows includes Git Bash)
- The free **claude-seo** skills by AgriciDaniel: <https://github.com/AgriciDaniel/claude-seo> (MIT). The system uses their Search Console, GA4, URL Inspection, PageSpeed and Moz tools.
- A free Google Cloud service account for Search Console and GA4 (`/seo google setup` in Claude Code walks you through it)

## Install

```bash
git clone https://github.com/ahmedabdoun92/seo-claude-system-kit.git
cd seo-claude-system-kit
python install.py
```

`install.py` checks the requirements, installs the `seo-claude-system` skill into `~/.claude/skills/` with this folder's path, and creates `clients/`. It downloads nothing and asks for no keys.

Then:

1. **Google data:** in Claude Code run `/seo google setup` (free service account; add its email to Search Console as a user and to GA4 as a Viewer).
2. **Optional free keys:** run `python system/setup/setup_keys.py` **in your own terminal** (Bing Webmaster, Open PageRank, Moz free tier). Keys never go in the chat.
3. **Start:** open Claude Code and say **"SEO Claude System"**. It checks your setup and onboards your first client.

You can also open Claude Code inside this folder: the skill is included in `.claude/skills/` as a project skill.

## How it works

1. **Onboard:** business facts from the owner, platform, competitors, customer questions.
2. **Baseline:** 90 days of Search Console and GA4, index status of every URL, speed, conversion tracking.
3. **Audit and fix:** technical and AI-readiness audits; fixes on a branch with a preview, written for the client's platform (custom code, WordPress, Shopify, Webflow, Wix…).
4. **Content:** gaps from AI answers and Search Console become guides and comparison pages.
5. **AI visibility:** a monthly round over every customer question.
6. **Loops:** scheduled per client from [`system/templates/scheduled-tasks/`](system/templates/scheduled-tasks/).

| When | Loop |
|---|---|
| Monday 09:00 | Weekly report |
| 1st, 09:00 | Technical check |
| 3rd, 10:00 | Client report |
| 17th, 10:00 | AI-visibility round |

## House rules (built in)

From [`CLAUDE.md`](CLAUDE.md): free tools only · business facts come from the owner, unknown stays `TBD` · every number has a source and date · one client at a time, each with its own Search Console property · planned features are never presented as done · keys never in chat · outreach and client reports are drafts the user sends · code changes are reviewed before they ship · everything is logged.

## Free data stack

Google Search Console · URL Inspection API · GA4 · PageSpeed Insights · Chrome UX Report · Bing Webmaster Tools · IndexNow · Open PageRank · Tranco · live web search · schema validation.
**Not used:** paid keyword and backlink databases. Where search volumes would help, the system says so instead of guessing.

## Your client data stays private

Client folders (`clients/<domain>/`) hold business details and Search Console data. They are git-ignored here. To back them up, keep your working copy in a **private** repository and run `python system/setup/backup.py` (weekly).

## Check the install

```bash
python system/tests/smoke.py
```

## Case study

The system's first client, a luxury travel agency in Egypt, went from 46 to 110 pages (English + Arabic), 13 to 35 indexed pages, and 18 to 86 weekly Google impressions in its first three days, with AI crawlers unblocked, mobile PageSpeed 95–100 and zero technical problems on the live site. Clicks and leads were still at zero at that point: the real test is the following months. Details on the overview page.

## Credits and licence

Built on [claude-seo](https://github.com/AgriciDaniel/claude-seo) by AgriciDaniel (MIT). This repository is MIT licensed: see [LICENSE](LICENSE).
