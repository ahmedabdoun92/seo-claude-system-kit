# SEO Claude System — departments and routing

10 departments × 5 roles. **Status:** `ready` = works now · `partial` = works with limits · `planned` = not built yet (say so; don't fake it).
"Use" is what to run for that role. All client work reads `clients/<domain>/client.json` + `profile.md` first.

## 1. SEO Strategy & Planning
| Role | Status | Use |
|---|---|---|
| seo-strategy | ready | `seo-plan` skill, fed with profile.md + competitors.md |
| competitor-analysis | ready | Competitor discovery in the entry skill + `system/scripts/competitor_numbers.py`; `seo-competitor-pages` for "X vs Y" pages |
| content-planning | partial | `content-strategy` + `seo-plan` |
| topic-mapping | ready | `seo-cluster` |
| seo-forecasting | planned | Phase 4: Search Console history + CTR curve |

## 2. Keyword & Prompt Research
| Role | Status | Use |
|---|---|---|
| keyword-research | planned | Phase 3: Search Console queries, Bing keyword tool, Google suggestions/People Also Ask via WebSearch, Google Trends |
| prompt-research | planned | Phase 3: grows `questions.md` |
| search-intent | ready | `seo-sxo`, `seo-cluster` |
| keyword-clustering | ready | `seo-cluster` |
| query-expansion | ready | `seo-cluster` |

## 3. Technical SEO & Audits
| Role | Status | Use |
|---|---|---|
| site-audit | ready | `seo-audit` |
| crawl-analysis | ready | `system/scripts/tech_audit.py` monthly live-site check (status, canonicals, titles, H1, thin/orphan pages, broken links, hreflang, crawler access, mobile PageSpeed; compares with last run); `seo-technical`, `seo-unlighthouse` for deep dives |
| indexation-check | ready | `weekly_report.py` re-checks every sitemap URL; `indexing_queue.py` gives today's 10 URLs to request; `seo-google` URL inspection for single pages |
| schema-markup | ready | `seo-schema` |
| core-web-vitals | ready | `seo-google` CrUX + PageSpeed (needs the Google API key) |

## 4. Content Briefs & Creation
| Role | Status | Use |
|---|---|---|
| content-briefs | ready | `seo-content-brief` |
| content-writing | ready | `playbook-content-pipeline.md` (fact sheet, sources, number check, bilingual, QA) + `copywriting` |
| content-editing | ready | `copy-editing`, `content-humanizer` |
| content-optimization | ready | `seo-content`, `seo-page` |
| content-calendar | partial | `content-strategy`; dated calendar file in Phase 3 |

## 5. On-Page SEO & Internal Linking
| Role | Status | Use |
|---|---|---|
| on-page-seo | ready | `seo-page` |
| internal-linking | ready | `system/scripts/link_map.py` (content links only, flags pages with fewer than 3; part of the monthly `tech_audit.py`); `seo-cluster` link matrix for planning |
| meta-optimization | ready | `seo-page` |
| entity-optimization | partial | `seo-geo` + `seo-schema`; full entity work in Phase 3 |
| sitemap-management | ready | `seo-sitemap` |

## 6. AI Search Visibility
| Role | Status | Use |
|---|---|---|
| ai-visibility | ready | `ai_visibility.py` monthly round (skill §7) + `seo-geo` readiness audit |
| answer-engine-tracking | ready | skill §7: agents sample one web-search answer per `questions.md` question; no paid trackers |
| brand-mentions | partial | `seo-geo` brand signals |
| prompt-monitoring | ready | `ai_visibility.py` compares each round with the last |
| visibility-insights | ready | `reports/ai-visibility-<date>.md` gaps + action plan |

## 7. Citation & Mention Building
| Role | Status | Use |
|---|---|---|
| citation-research | ready | `ai_visibility.py` top cited sources per round |
| source-analysis | partial | by hand in the AI-visibility report (which source wins which topic) |
| mention-building | partial | `public-relations`; `playbook-reviews-and-gbp.md` for reviews and business profiles |
| expert-quotes | planned | Phase 4: drafts only; the user sends |
| citation-tracking | ready | `ai_visibility.py` client cited / mentioned counts vs last round |

## 8. Link Building & Digital PR
| Role | Status | Use |
|---|---|---|
| link-prospecting | partial | `seo-backlinks` on competitors; prospect lists in Phase 4 |
| digital-pr | ready | `public-relations` |
| outreach | ready | `cold-email` (drafts only; the user sends) |
| linkable-assets | partial | `lead-magnets`, `free-tools` |
| backlink-analysis | ready | `seo-backlinks` |

## 9. Content Refresh & Recovery
| Role | Status | Use |
|---|---|---|
| content-refresh | planned | Phase 2 |
| decay-analysis | ready | `weekly_report.py` decay alerts (pages losing ≥30% impressions or half their clicks week over week) |
| content-recovery | planned | Phase 2 |
| freshness-check | partial | `seo-drift` |
| redirect-review | partial | `seo-technical` |

## 10. SEO Reporting & Analytics
| Role | Status | Use |
|---|---|---|
| seo-reporting | ready | `weekly_report.py` (weekly, incl. Bing and open owner tasks) + `client_report.py` (monthly client-facing HTML) + `clients_overview.py` (all clients) |
| rank-tracking | ready | `system/scripts/weekly_report.py` (weekly query/page snapshots + movers, new/lost searches, quick wins) |
| traffic-analysis | ready | `seo-google` GA4 (pass the client's `--property`) |
| conversion-tracking | ready | `weekly_report.py` + `ga4_events.py` (live-host-only event counts by page); `ga4_money_pages.py` for a 90-day view; `analytics` to set up tracking |
| performance-insights | ready | `weekly_report.py` "What to do this week" list |

## Build phases
1. **Foundation** (done): setup, client folders, onboarding, competitor discovery, customer questions.
2. **Data from Search Console** (built 2026-10-17): weekly report with rank tracking, decay alerts, indexing tracker and conversions. Monthly technical check (`tech_audit.py`) added 2026-10-19. Keyword-gap and page-vs-top-10 loops are scheduled to be built once Search Console has enough data (check on 2026-11-09). Refresh/recovery content work still uses the decay list by hand.
3. **Research and content:** keyword and prompt research, writing pipeline, calendar, internal links, entities.
4. **AI and authority:** AI visibility tracking and citation research built 2026-10-17 (`ai_visibility.py`, skill §7). Still planned: expert quotes, link prospecting, forecasting.

## Operations (not a department)
| Tool | Use |
|---|---|
| `system/setup/check_client.py` | Validates a client folder, settings and scheduled loops |
| `system/tests/smoke.py` | Health check of every script and template (about 8 seconds) |
| `system/setup/backup.py` | Git backup of the system (weekly, Mondays 11:30) |
| `tech_audit.py` lead path | `client.json` → `monitor_urls`: forms, publish hooks, booking links answer as expected |
| Playbooks | `system/reference/playbook-*.md`: multilingual, content pipeline, site changes, reviews & business profiles |
