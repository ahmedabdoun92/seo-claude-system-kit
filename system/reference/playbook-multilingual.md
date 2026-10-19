# Playbook: adding a second language to a client site

Use when a client wants their site in a second language (example used here: Arabic, right-to-left).
Read the client's `client.json`, `profile.md` and their section in `platforms.md` first.
Follow `playbook-site-changes.md` for every code change (branch, checks, preview, merge).

## 0. Before starting: decisions the owner makes
| Decision | Options | Default if owner agrees |
|---|---|---|
| Language style | Formal standard (Arabic: Modern Standard Arabic) or dialect | Formal standard for pages; dialect only for social posts |
| Reviewer | Native speaker on the owner's side checks each batch before merge | Required; no merge without it |
| Where translated business text lives | CMS/admin fields per language, or in code (Claude maintains it) | Owner chooses; write it in `profile.md` |
| Admin/back office | Translate or keep in one language | Keep in the main language |
| Scope | All pages, or a phased list | Phased (section 6) |

Write a short feasibility note first (`clients/<domain>/reports/<date>-<lang>-site-plan.md`): why (demand evidence: non-English questions in `questions.md`, AI-visibility answers in that language, Search Console queries), what the site has today, word count to translate, phases, decisions needed, cost.

## 1. URL structure
| Rule | Detail |
|---|---|
| Subfolder | `/ar/` for the new language; main language stays at root. No subdomains, no `?lang=` parameters, no cookie/IP-based switching. |
| Same slugs | `/hotels/x/` -> `/ar/hotels/x/`. Latin slugs stay readable when shared and make pairing pages trivial. |
| One page = one language | Never publish a half-translated page. A page goes live in the new language only when fully translated. |
| Language switch | Visible link in the header to the twin page (not to the home page). A plain link, not a script redirect. |
| Canonical | Each language version is self-canonical. Never canonical the Arabic page to the English one. |

## 2. hreflang
| Rule | Detail |
|---|---|
| Values | `en`, `ar`, `x-default` (x-default -> main-language page). Add region codes only if the content truly differs per country. |
| Where | In the `<head>` of every page AND in the XML sitemap (`xhtml:link` entries). Both must agree. |
| Reciprocal | The English page lists the Arabic twin and itself; the Arabic page lists the English twin and itself. Missing return links = ignored. |
| Only real twins | List a language only if that page exists and returns 200 in that language. |
| Absolute URLs | Use the canonical host (`https://www.example.com/ar/...`), trailing-slash style identical to the canonical. |

Check: `seo-hreflang` skill, and the monthly `python system/scripts/tech_audit.py <domain>` (checks hreflang).

## 3. HTML language and direction
- `<html lang="ar" dir="rtl">` on Arabic pages; `<html lang="en" dir="ltr">` on English pages. Set server-side / in the pre-rendered HTML, not only after JavaScript.
- Schema JSON-LD: `inLanguage: "ar"` on Arabic pages; translated `name`/`description` where shown on the page.
- `og:locale` = `ar_AR` (or the market's locale), `og:locale:alternate` = the other language.

## 4. RTL layout and typography
| Item | Do |
|---|---|
| Direction-aware CSS | Replace left/right with logical start/end: `margin-inline-start`, `padding-inline-end`, `text-align: start`, `inset-inline-start`. Tailwind 3.4+: `ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`. Count left/right uses before starting (grep) to size the work. |
| Icons | Mirror direction icons (arrows, chevrons, "next"). Do not mirror logos, play buttons, numbers. |
| Letter-spacing | None on Arabic text (it breaks joined letters). Remove `tracking-*` / `letter-spacing` and uppercase styles for Arabic. |
| Line-height | More relaxed than Latin (around 1.6–1.8 for body text). |
| Font | A free Arabic font (e.g. Cairo, IBM Plex Sans Arabic, Noto Sans Arabic), self-hosted, Arabic subset only, `font-display: swap`, and `<link rel="preload">` for the main weight on Arabic pages only. Preloading fixes the layout shift caused by the font swap. |
| Numbers | Pick Western (0-9) or Arabic-Indic digits once and use it everywhere; prices and phone numbers stay readable with `dir="ltr"` spans if needed. |
| Forms | Translated labels, errors and placeholders; phone/email fields `dir="ltr"`. Pre-filled WhatsApp/email messages in the page's language. |

## 5. Translation method
1. **Style:** Modern Standard Arabic by default (reads well across Egypt and the Gulf). Other languages: the standard written form.
2. **Facts are identical.** Prices, dates, distances, star ratings, ages, counts, phone numbers and names do not change in translation. Translate words, not facts. Nothing new is added that the source page does not say.
3. **Glossary first.** Before translating, fix one translation per recurring term (brand name, product/service names, place names, "all-inclusive", "adults-only", UI words). Save it in the client folder (`clients/<domain>/content/glossary-<lang>.md`) and give it to every translator agent.
4. **UI strings** in one dictionary file (key -> en / ar), not scattered in components.
5. **Parallel agents are fine** for volume (split by page group), all using the same glossary.
6. **Automated number check** after translation: every number in the English page must appear in the translation (and no extra numbers). Convert Arabic-Indic digits to 0-9 before comparing. Minimal check:
   ```python
   import re
   AR = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
   nums = lambda t: sorted(re.findall(r"\d+(?:[.,]\d+)?", t.translate(AR)))
   missing = set(nums(en_text)) - set(nums(ar_text))   # must be empty
   extra   = set(nums(ar_text)) - set(nums(en_text))   # review each
   ```
7. **Owner review on a preview** (Netlify/hosting preview of the branch) before merge. The owner's native-speaker reviewer reads it; Claude fixes what they flag.
8. Meta titles/descriptions are written in the new language (not left in English), same length limits as English.

## 6. Phased rollout
| Phase | Pages | Why first |
|---|---|---|
| A. Framework + core | Routing, RTL, font, dictionary, hreflang, sitemap, language switch; home, main listings (products/hotels/services), category/destination pages, FAQ, About/trust page, contact form | Makes the language usable and indexable |
| B. Answer pages | Pages that answer the customer/AI questions in that language (from `questions.md` and the AI-visibility gaps), plus the money pages (top products/hotels) | Fastest wins in AI answers and search |
| C. The rest | Remaining guides, legal pages (privacy/terms), feeds (`/ar/feed.xml`), `llms.txt` section or `/ar/llms-full.txt` | Completes the site; every page has a twin |

After each phase goes live: resubmit the sitemap in Search Console, request indexing for the new language's home and key pages (`seo-google`), add a line to `log.md`.

## 7. Performance
- **Load translation text only on that language's pages.** On a JavaScript site, put the second language's content in a separate chunk loaded on `/ar/` routes only. Otherwise every English page downloads all the Arabic text.
- Measure **PageSpeed (mobile) before and after each phase** on: home in each language, one product/hotel page in each language, one guide in each language. Record score, LCP, CLS in `log.md`.
- Watch main JS size in the build output each phase; a jump in size is the usual cause of LCP regressions.
- Font: subset + preload (section 4). Target CLS < 0.1.

## 8. Platform notes (high level)
| Platform | How the second language is done | Notes |
|---|---|---|
| Custom code (React/Next.js/static) | Claude builds routes, dictionary, hreflang, sitemap, RTL CSS in the repo | Make sure pages are pre-rendered/server-rendered per language |
| WordPress | WPML (paid) or Polylang (free core; paid Pro); both add hreflang and language subfolders | Check the SEO plugin (Yoast/Rank Math) integrates with it; theme must support RTL (`rtl.css`) |
| Shopify | Shopify Markets + Translate & Adapt app (or another translation app); languages served as `/ar/` subfolders with automatic hreflang | Theme RTL support varies; check the theme before promising RTL |
| Webflow | Webflow Localization (paid add-on) gives subfolders + hreflang | Translations per locale in the Designer/CMS |
| Wix / Squarespace / Salla / Zid | Built-in multilingual features; check RTL and hreflang output | Confirm in `platforms.md` and with a live test page |

On CMS platforms Claude delivers exact steps and translated text; the owner clicks (see `playbook-site-changes.md`, CMS section). Paid plugins/add-ons are the owner's choice; mention the free option where one exists.

## 9. Checklist
- [ ] Owner decisions recorded (style, reviewer, where text lives, scope)
- [ ] Glossary file saved
- [ ] `/ar/` subfolder, same slugs, self-canonical
- [ ] `<html lang dir>` correct in server HTML on both languages
- [ ] hreflang en/ar/x-default in head and sitemap, reciprocal, only real twins
- [ ] Logical start/end CSS; direction icons mirrored
- [ ] No letter-spacing on Arabic; relaxed line-height
- [ ] Arabic font self-hosted, subset, preloaded on Arabic pages only
- [ ] UI strings, forms, WhatsApp/email messages translated
- [ ] Meta titles/descriptions in the new language
- [ ] Number check passed for every translated page
- [ ] Translation text loaded only on that language's pages
- [ ] Build + SEO checks pass; preview checked desktop + mobile, both languages
- [ ] Owner's reviewer approved on the preview
- [ ] PageSpeed before/after recorded
- [ ] Sitemap resubmitted, indexing requested, `log.md` updated

## Worked example: reservella.net (2026-10-17/18)
Custom React + Vite site on Netlify. Demand: 18 of 34 customer questions were Arabic. Owner chose MSA, Admin stays English.
Phase A (PR #12): 12 Arabic pages, RTL, Cairo font, hreflang. Phase B (PR #13): 27 hotel pages + 6 answer guides, number check passed. PageSpeed then dropped on hotel pages (main JS 488 -> 842 KB raw); fix (PR #14) moved Arabic text to a chunk loaded only on `/ar/` (main JS back to ~604 KB) and scores recovered to 95–100. Phase C (PR #15): every English page has an Arabic twin (54 + 54). Arabic font preload then cut CLS on `/ar/` from 0.092 to 0.003. Details: `clients/reservella.net/log.md`, `reports/2026-10-17-arabic-site-plan.md`.
