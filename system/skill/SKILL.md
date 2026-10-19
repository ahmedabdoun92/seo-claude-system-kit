---
name: seo-claude-system
description: Entry point for the multi-client "SEO Claude System" — a full SEO department (10 departments × 5 roles) for any client website. Use whenever the user says "SEO Claude System", "using SEO claude system", "SEO system", or asks to run the SEO department for a client, domain or brand. Onboards new clients (asks for the business details and site platform when no client folder exists), finds the 3-5 biggest competitors with free numbers, drafts customer questions, checks free API setup, and routes every SEO task to the right department skill.
---

# SEO Claude System

Home folder: `{{HOME_SCS}}` (called `$HOME_SCS` below). Read `$HOME_SCS/CLAUDE.md` first: its house rules apply to everything here (free tools only, never invent facts, keys never in chat, drafts only for outreach).

Reply in the user's language. Keep messages short and plain.

## 1. Work out what was asked

| User says | Do |
|---|---|
| "check setup" / "setup" | §2 Setup check |
| "setup keys" / "add keys" | §2 Key setup |
| "list clients" / "clients" | `python "$HOME_SCS/system/scripts/new_client.py" --list` and show the table |
| "<client> weekly report" / "check indexing" / "how are we doing" | §6 Weekly report |
| "<client> AI visibility" / "are we in ChatGPT / AI answers" / "who gets cited" | §7 AI visibility |
| "<client> technical check" / "monthly audit" / "is anything broken" | §8 Monthly technical check |
| "clients overview" / "all clients" | `python "$HOME_SCS/system/scripts/clients_overview.py" --md` and show the table |
| "<client> indexing list" / "what should I request today" | `python "$HOME_SCS/system/scripts/indexing_queue.py" <domain>` (add `--mark` once the owner has requested them) |
| "<client> monthly client report" | §10 Client report |
| "run everything for <client>" / "full run" / "A to Z" | §11 Full run |
| "check <client> setup" / "is the system healthy" | `python "$HOME_SCS/system/setup/check_client.py" <domain>` and `python "$HOME_SCS/system/tests/smoke.py"` |
| a domain, brand or client name | §3 Client flow |
| only "SEO Claude System" | List clients (above). Ask which client to work on, or whether to add a new one |
| an SEO task without a client | Ask which client (show the list) |

## 2. Setup

**Setup check:** run `python "$HOME_SCS/system/setup/check_setup.py" --json` (add `--client <domain>` when a client is known). Show a short table: tool, works?, what it unlocks, fix. For anything missing, give the exact fix from the output. If `masked_google_env_var` is true, explain that the Windows `GOOGLE_API_KEY` variable holds the masked display copy (`AIza••••`) from the Google console, not a real key.

**Key setup:** keys are typed by the user into `setup_keys.py`, never into the chat. If the terminal tool `mcp__terminal__run_in_terminal` is available, start `python "$HOME_SCS/system/setup/setup_keys.py"` there and tell the user to paste keys into that terminal tab; otherwise give them that command in a `bash` code block. One key only: add `--only google|bing|opr|moz`. When they say they're done, run the setup check.

If the user pastes a key into the chat anyway: don't repeat it, tell them to run `setup_keys.py` instead, and suggest they regenerate that key since it is now in the chat history.

## 3. Client flow

Normalise the domain (no `https://`, no `www.`). The client folder is `$HOME_SCS/clients/<domain>/`.

- **Folder missing →** §4 Onboarding.
- **Folder exists →** read `client.json`, `profile.md` and the top of `log.md`. If any `onboarding` flag is false, say what's left and continue from that step. Otherwise do the requested task (§5), or, with no task, show a 3-line status (platform, last work from the log, what's set up) and the department menu.

## 4. Onboarding a new client

Ask before creating anything. Skip questions the user has already answered.

**4a. Business questions.** Send one message with a short numbered list:
1. Business name and website domain
2. What you sell: main products/services, and the top 3 to grow
3. Who your customers are, and the problems they want solved
4. Countries/cities you sell to; do customers visit a physical location?
5. Languages customers search in (e.g. Egyptian Arabic, Gulf Arabic, English)
6. Main goal: sales, leads, bookings, calls or sign-ups
7. Pages that bring in money (URLs), if you know them
8. Competitors you already know (optional; I'll search for the big ones anyway)
9. Brand tone, and anything to avoid saying

Then use AskUserQuestion for the site:
- **Platform:** WordPress / Shopify / Wix, Webflow or Squarespace / Custom code (Next.js, React, Laravel…). "Other" covers Salla, Zid, YouCan and the rest.
- **Access:** "Claude edits the site files" (only for code in a local folder or repo) / "Recommendations only".
- **Google data:** "Search Console + GA4 exist" / "Only Search Console" / "Neither yet".

**4b. Create the folder.** `python "$HOME_SCS/system/scripts/new_client.py" <domain> --json`. Fill `profile.md` with the answers (unknown stays `TBD`) and `client.json` (`business_name`, `platform`, `site_access`, `markets`, `languages`). Set `onboarding.profile = true`. Read the platform's section in `$HOME_SCS/system/reference/platforms.md`; from now on, every fix is written for that platform.

**4c. Access check.** `python "$HOME_SCS/system/setup/check_setup.py" --client <domain> --quick --json`.
- Search Console found → save `gsc_property` in `client.json`.
- Not found → tell the user: Search Console → Settings → Users and permissions → Add user → the `service_account_email` from the output → Full. Same email as Viewer in GA4 (Admin → Property access management), then ask for the numeric GA4 property ID and save it as `ga4_property_id`.
- Bing missing → Bing Webmaster Tools → Add site → Import from Google Search Console.
Don't block on this; continue to 4d. Set `onboarding.access_checked = true`.

**4d. Competitor discovery** (the user wants the big competitors found for them, with names and numbers).
1. Write 8–12 searches from the profile: main services × markets, "best <service> in <city>", the same in each market language (Arabic queries for Arabic markets), "<brand> alternatives" if the brand is known. Run them with WebSearch in one turn.
2. Tally which domains show up and in how many searches. Sort each into: **direct competitor** (a business selling the same thing), **marketplace/aggregator**, **directory/review site**, **media/social/wiki**, or the client itself. When unsure what a site sells, WebFetch its homepage.
3. Take the top ~8 direct competitors plus any the user named and run
   `python "$HOME_SCS/system/scripts/competitor_numbers.py" <client-domain> <c1> <c2> ... --json --save <client-domain>`
   (put the client first, for comparison). Add `--moz` only for the final 3–5, only if Moz is set up, and mention that it uses the free monthly quota.
4. Choose the **3–5 big competitors**: first by how many of the searches they appear in (they fight for the same customers), then by size (Open PageRank, referring domains, Tranco rank, Chrome real-user data). Say why each made the list.
5. Write `competitors.md`:
   - Table: # · Name · Domain · What they sell · Seen in X of N searches · Tranco rank · Open PageRank · Referring domains · Chrome real-user data · Moz DA (if run). Put the client's row last, in bold.
   - "SERP rivals" table: marketplaces, directories and media taking the same searches.
   - The searches used, today's date, the data sources, and the limits: web search results are not a localised Google ranking report; a missing number means the source had no data or the key isn't set up.
6. Show the table and ask the user to confirm, remove or add. After they confirm, set `onboarding.competitors = true`.

**4e. Customer questions.** Draft 30 questions (20–50) that customers ask Google or ChatGPT before buying, written the way they'd really type them, in the market's languages. Group them under Awareness, Comparison (including "X vs <competitor>"), Decision (price, trust, location, delivery) and After purchase. Save them to `questions.md`, marked `draft`, then ask the user to approve or edit. After approval, mark them `approved` and set `onboarding.questions = true`.

**4f. Hand-off.** Log each onboarding step in `log.md`. Show the department menu and suggest the 3 most useful first tasks for this business, for example a site audit, a Search Console report and a content plan.

### 4g. Schedule the client's loops and to-do list
Copy `system/templates/client/todo.md` into the client folder (owner / Claude / waiting). Then create the client's scheduled tasks from `system/templates/scheduled-tasks/` (see its README): fill `{{DOMAIN}}`, `{{SITE_URL}}`, `{{BRAND}}` and `{{HOME_SCS}}` and use the cron in the README: weekly report `0 9 * * 1`, monthly technical check `0 9 1 * *`, monthly AI-visibility round `0 10 17 * *`, monthly client report `0 10 3 * *`. Without the desktop app's scheduler, tell the user how to run them by hand. Add the lead-path URLs (forms, booking links, checkout, publish hooks) to `client.json` → `monitor_urls`. Finish with `python "$HOME_SCS/system/setup/check_client.py" <domain>`: every line should PASS.

## 5. Doing SEO work for a client

1. Find the role in `$HOME_SCS/system/reference/departments.md` and use the skill listed there, passing the client's context: domain, `gsc_property`, `ga4_property_id`, platform, markets, languages, competitors.
2. `planned` roles aren't built yet. Say so, and offer the closest ready alternative.
3. Save outputs under the client folder (`reports/`, `data/`, `content/`, `snapshots/`), date-stamped, and add a line to `log.md`.
4. Any fix is written for the client's platform (see `platforms.md`). With "Recommendations only" access, never edit files; give the steps and the exact text to paste.

## Department menu (show this when asked "what can you do")

1 Strategy & Planning · 2 Keyword & Prompt Research · 3 Technical SEO & Audits · 4 Content Briefs & Creation · 5 On-Page & Internal Linking · 6 AI Search Visibility · 7 Citations & Mentions · 8 Link Building & PR · 9 Content Refresh & Recovery · 10 Reporting & Analytics.
Show each one's ready / partial / planned roles from `departments.md`.

## 6. Weekly report (rank tracking, decay, indexing, conversions)

Run `python "$HOME_SCS/system/scripts/weekly_report.py" <domain>` (about 5 seconds per sitemap URL for the indexing check; add `--no-inspect` for a fast run without it). It compares the last complete Search Console week with the week before, re-checks every sitemap URL in Google, counts GA4 conversion events on the live host only, saves `snapshots/gsc-week-<date>.json` and `snapshots/index-<date>.json` for next time, writes `reports/weekly-<date>.md` and adds a log line.

Then tell the user, in plain words: the headline numbers (clicks, impressions, indexed pages, conversions) versus last week, what moved, any decay or dropped pages, and the "What to do this week" list. Point them at the report file. Optional per-client settings in `client.json`: `conversion_events` (GA4 event names). The first two reports mostly show "new vs baseline"; trends become meaningful after 2–4 weeks.

## 7. AI visibility (answer sampling, citations, competitors)

Free method: one web search per customer question in `questions.md`, run by parallel agents (about 8–9 questions each, all languages the client serves). Each agent returns one JSON object per question: `id, question, lang, cited_domains, client_cited, client_mentioned, brands_mentioned, answer_gist, answer_quality (good|weak|none)`. `client_mentioned` is true only when the answer names the client on its own, not just because the question did. Retry a question once if the search was rate-limited; never record an answer that had no sources as "good".

1. Save the parts to `clients/<domain>/data/_ai-round/`, merge into `round-<date>.json` (check all ids are present).
2. Run `python "$HOME_SCS/system/scripts/ai_visibility.py" <domain> <round.json> --json`. It scores citations, mentions, OTA share, results per language and the `competitor_domains` from `client.json`, compares with the last `data/ai-visibility-*.json`, and writes `reports/ai-visibility-<date>.md`.
3. Add the analysis to that report by hand: which sources AI trusts per topic (citation targets), questions with weak or no answers (content gaps the client can own), brand problems (look-alike names, no reviews), and a short action plan tagged [code] / [owner] / [content] / [outreach — drafts only].
4. For a site readiness check, run the `seo-geo` agent (AI crawler access, llms.txt, citable passages, schema, entity signals).

Repeat monthly; it is a sample of AI web-search answers, not a full ChatGPT / Perplexity / AI Overviews tracker (those are paid), so say so.

## 8. Monthly technical check

Run `python "$HOME_SCS/system/scripts/tech_audit.py" <domain>` (3–5 minutes; `--no-psi` skips PageSpeed). It crawls every sitemap URL on the live site and flags non-200 pages, redirects, foreign canonicals, noindex pages in the sitemap, missing/duplicate/long titles, meta description length, H1 count, thin (<300 words) and orphan pages, broken internal links, hreflang pairs that do not point back, wrong `<html lang>`, robots.txt / sitemap / llms.txt reachability, AI and search crawler access, and mobile PageSpeed for 4 sample pages. It compares with the previous run (new vs fixed), writes `reports/tech-audit-<date>.md`, saves `data/tech-audit-<date>.json` and adds a log line.

Tell the user the headline (pages, OK, problems, new vs fixed), the new problems with their fix, and who does each fix (code via a branch, or the owner in Admin / Cloudflare / Search Console). A single PageSpeed score of 85–90 is normal lab variance. Schedule it monthly per client (scheduled task, cron `0 9 1 * *`).

## 9. Backups and link map

- `python "$HOME_SCS/system/setup/backup.py"` commits the whole SEO System folder (plus a copy of this skill and the client scheduled tasks) and pushes to its **private** GitHub remote. It runs every Monday at 11:30. Keys are never in this folder.
- `python "$HOME_SCS/system/scripts/link_map.py" <domain>` maps internal links from page content only (menus and footers ignored) and lists pages with fewer than 3; the monthly check includes it.

- **Public kit (shareable copy, no client data):** `python "$HOME_SCS/system/setup/export_public.py" --dest <public repo folder>` rebuilds the public repo from this system (scripts, setup, templates, reference, skill, overview page), replaces local paths with placeholders and stops if its privacy scan finds keys, emails, property ids or personal paths. Then commit and push in that folder. Client folders are never exported.

## 10. Client report, to-do lists and playbooks

- `python "$HOME_SCS/system/scripts/client_report.py" <domain> --month YYYY-MM [--lang ar]` writes a branded, client-facing HTML report (`reports/client-report-<month>.html`) from the weekly snapshots, indexing, technical check, AI visibility, log and todo.md. Only real data; sections without data are skipped.
- Every client has `todo.md` (Owner / Claude / Waiting). Update it after each piece of work; the Monday report lists the open owner and waiting items.
- Playbooks in `system/reference/`: `playbook-multilingual.md`, `playbook-content-pipeline.md`, `playbook-site-changes.md`, `playbook-reviews-and-gbp.md`. Follow them for those jobs.

## 11. Full run, A to Z ("run everything for <client>")

Runs every ready part of the department for one client and ends with one summary report. Long steps run in the background while agents work in parallel.

| Step | What | How |
|---|---|---|
| A. Setup | Tools and client health | `check_setup.py --client <domain> --json`, `check_client.py <domain>` |
| B. Search data | Weekly report: rankings, movers, decay, index status of every URL, Bing, conversions | `weekly_report.py <domain>` (background) |
| C. Technical | Live crawl, link map, crawler access, lead-path URLs, mobile PageSpeed | `tech_audit.py <domain>` (background, after B) |
| D. Competitors | Fresh authority numbers for the client and its competitors | `competitor_numbers.py <domain> <competitor_domains…> --json` (show the numbers; keep `competitors.md` unless the user approves changes) |
| E. AI visibility | The monthly round over every question in `questions.md` | §7 with 4 parallel agents |
| F. AI readiness | Crawler access, llms.txt, citable passages, entity signals, vs the last audit | `seo-geo` agent → `reports/geo-audit-<date>.md` |
| G. Content quality | E-E-A-T, depth, thin/duplicate text, translation accuracy | `seo-content` agent → `reports/content-audit-<date>.md` |
| H. Structured data | JSON-LD per page type, cross-page and cross-language consistency | `seo-schema` agent → `reports/schema-audit-<date>.md` |
| I. Indexing | Today's 10 URLs to request | `indexing_queue.py <domain>` |
| J. Client report | Last complete month (and the current month so far, if useful) | `client_report.py <domain> [--lang …]` |
| K. Overview | All clients in one table | `clients_overview.py --md` |
| Z. Summary | One report: scores, what changed, every finding de-duplicated and ranked, each tagged [code] / [owner] / [content] / [outreach — drafts only], plus what was skipped and why | `reports/full-run-<date>.md`, a log line, `todo.md` updated, `backup.py` |

Agents are read-only: they write their report and change nothing else. Fixes are proposed, not made: code fixes go on a branch only when the user says so.
