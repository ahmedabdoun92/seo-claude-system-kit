# Playbook: from content gap to published guide

Use for every new guide, comparison or FAQ-style page on a client site.
Read `client.json`, `profile.md`, `questions.md` and the client's section in `platforms.md` first.
Code changes follow `playbook-site-changes.md`; second-language versions follow `playbook-multilingual.md`.

## 1. Find the gap
| Source | How | What counts as a gap |
|---|---|---|
| AI visibility | Latest `reports/ai-visibility-<date>.md` (`ai_visibility.py`, skill §7) | Questions with weak or empty answers, or answers that cite only OTAs/marketplaces/portals |
| Search Console | `weekly_report.py` quick wins, or `seo-google` queries for the client's `--property` | Queries at average position 8–30 with impressions, where no page answers the query directly |
| Customer questions | `questions.md`, owner's inbox/WhatsApp FAQs (as given by the owner) | Questions with no page that answers them |
| Competitors | `competitors.md`, `seo-competitor-pages` | Comparison/"X vs Y" topics the client can answer with its own facts |

Pick pieces by: matches a money page (product/hotel/service) > answers several questions at once > search demand. Write the chosen topics and the questions each one targets (by number in `questions.md`) in the plan.

## 2. Fact sheet (one per piece)
Save as `clients/<domain>/content/<date>-<slug>-facts.md` before writing.

| Section | Rules |
|---|---|
| Business facts | Only what the owner confirmed (from `profile.md` or the owner in chat). Prices, policies, payment, booking steps. Unknown = `TBD`; never fill a gap with a guess. |
| Third-party facts | Official sources first (the hotel/manufacturer/government site), each with URL and **date checked**. Marketplaces/OTAs only when the official source is silent, and say so. |
| Conflicts | If sources disagree, list both and flag it for the owner; do not pick one silently. |
| Not allowed | Invented reviews, ratings, awards, customer numbers, quotes, "best" claims without a source. |

## 3. Brief and structure (answer-first)
Use `seo-content-brief` for the brief. Every piece follows this order:

1. **H1** with the main question/topic.
2. **Short answer** (2–4 sentences) right under the H1: the direct answer, with the key number/fact.
3. **Comparison table** where there is more than one option (prices, features, distances, who it suits).
4. **Body sections** (H2 per sub-question), short paragraphs, each section answerable on its own.
5. **How to book / next step** with a link to the money page or contact.
6. **FAQs** (4–8, real questions from `questions.md`/Search Console) with `FAQPage` schema matching the visible text.
7. Visible **"last checked <date>"** line and `dateModified` in schema.

Length: whatever answers the question fully; on the first client guides ran ~900–1,100 words.

## 4. Meta and on-page
| Item | Rule |
|---|---|
| Title | 20–70 characters, main topic first, brand at the end if space |
| Meta description | 70–165 characters, contains the answer or the key fact, no clickbait |
| URL | Short, lowercase, hyphens, under the right section (`/blog/<slug>/`) |
| Schema | `Article`/`BlogPosting` + `FAQPage` (+ `BreadcrumbList`); check with `seo-schema` |
| Images | Only licensed/owned images; descriptive alt text; sized and lazy-loaded below the fold |

## 5. Internal links
- **To the new piece:** from the related product/hotel/service pages and from category/destination pages, plus the blog index. At least **3 incoming content links** (inside the main content, not menu/footer).
- **From the new piece:** to every product/hotel page it mentions and to 2+ related guides.
- Check with `python system/scripts/link_map.py <domain>` (flags pages with fewer than 3 content links).

## 6. Translation
If the client has a second language, translate after the English version is final, using the glossary and rules in `playbook-multilingual.md` section 5. Both versions go in the same branch.

## 7. Number check
Every number in the fact sheet that appears in the piece must match the fact sheet; every number in the original must appear in the translation (script in `playbook-multilingual.md` section 5). Fix or flag every mismatch before the preview.

## 8. Build, checks, preview, merge
1. Build locally; run the site's SEO checks (e.g. `npm run check:seo` where the repo has one) and fix all errors.
2. Browser preview: desktop + mobile, every language version.
3. Commit + push the branch; owner opens the PR and reviews the hosting preview (for a second language, their reviewer reads it).
4. Owner merges. Verify live: page returns 200, is in the sitemap, schema valid.

## 9. After publishing
1. Request indexing for the new URLs (Search Console URL Inspection; `seo-google`). Keep a list in `reports/indexing-requests.md` if there are more than a few per day.
2. Resubmit the sitemap if the sitemap URL count changed a lot.
3. Add a line to `log.md`: date, department, URL(s), word counts, sources, questions targeted, branch/PR.
4. Next AI-visibility round and weekly report: check whether the targeted questions/queries moved.

## QA checklist
- [ ] Gap source named (AI question #, Search Console query, or customer question)
- [ ] Fact sheet saved; every business fact owner-confirmed; every outside fact has a source + date checked
- [ ] No invented numbers, reviews, quotes or awards; unknowns are `TBD` or left out
- [ ] Short answer under the H1
- [ ] Comparison table (when there are options)
- [ ] FAQs visible and in `FAQPage` schema, matching text
- [ ] Title 20–70 chars; description 70–165 chars
- [ ] "Last checked" date visible; `dateModified` set
- [ ] ≥3 incoming content links; links out to every mentioned money page
- [ ] Translation done (if bilingual) and number check passed
- [ ] Build + SEO checks pass; preview checked desktop + mobile, all languages
- [ ] Owner approved and merged
- [ ] Live 200, in sitemap, indexing requested, `log.md` updated

## Worked example: reservella.net
Gaps came from the first AI-visibility round (16 weak/empty answers out of 34). Six guides were written (e.g. hotel rates for Egyptians, residents and Gulf guests; how to get to Tawila Island; travel agency or Booking.com) from hotel guides built on official sites (checked 2026-10-17) and owner-given pricing; each targeted named question numbers. Each was linked from hotel and destination pages, translated to Arabic with a number check, built with `check:seo`, reviewed on the Netlify preview, merged, then listed for indexing requests. Details: `clients/reservella.net/log.md`.
