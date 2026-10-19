# Playbook: changing a client site safely

Use for every change Claude makes to a client's site code (fixes, content, schema, speed, redirects).
Read `client.json` (`site_access`, `code_path`, `repo`, `repo_branch`, `hosting`, `canonical_host`) and the client's section in `platforms.md` first.
If `site_access` is not "claude-edits", skip to section 6.

## 1. Who does what
| Step | Claude | Owner |
|---|---|---|
| Branch, code, build, checks, local preview | Yes | — |
| Commit + push the branch | Yes, after the owner's OK for that change | Says yes |
| Open the PR, review hosting preview | Can prepare the PR text | Opens/reviews (or approves Claude opening it) |
| Merge to the live branch | No | Yes |
| Verify live, measure, log | Yes | — |

## 2. Needs the owner's explicit approval (every time)
- Anything that goes public: merge/deploy, publishing posts, social or GBP content.
- Accounts and logins: creating accounts, passwords, API keys (keys go through `python system/setup/setup_keys.py` in the owner's terminal, never in chat).
- DNS, Cloudflare settings (bot rules, redirects, caching), email records.
- Payments, plans, paid add-ons, billing on any platform.
- Database changes on the live backend (Claude writes the SQL; the owner runs it).
- Deleting pages or content, changing URLs (needs 301s), robots.txt/noindex changes.

## 3. Steps
1. **Branch per change.** From the up-to-date live branch: `<topic>` name (e.g. `internal-links`, `arabic-phase-a`). One topic per branch so a problem can be reverted alone. Never work on the live branch directly.
2. **Make the change.** Keep the diff small and on topic. Show the owner the diff summary for anything non-trivial.
3. **Build locally.** The project's build (and pre-render) must pass with no new errors.
4. **Automated SEO checks.** The repo's own checks (e.g. `npm run check:seo`) plus, as relevant: schema (`seo-schema`), internal links (`link_map.py` after deploy), hreflang (`seo-hreflang`). Fix every failure before going on.
5. **Browser preview.** Run the local build and check the changed pages at desktop and mobile width, in every language the site has: layout, text, links, forms, no console errors.
6. **Commit** with a clear message: what changed and why (e.g. "Add Arabic hotel pages for 27 live hotels; hreflang in sitemap"). Never commit secrets or `.env` files.
7. **Push** the branch.
8. **Owner opens the PR** and reviews the hosting preview (Netlify deploy preview, Vercel preview, etc.). For translated content, their native-speaker reviewer reads it here. Claude fixes anything flagged on the same branch.
9. **Owner merges.**
10. **Verify live** (after the deploy finishes):
    - `curl -sI https://<canonical_host>/<path>` -> 200 for changed pages; old URLs -> one 301 hop to the new URL.
    - Page source shows the change (title, schema, hreflang, content) in the server HTML.
    - PageSpeed mobile for 2–3 changed pages (`seo-google` PageSpeed), compared with before.
    - `python system/scripts/tech_audit.py <domain>` for bigger changes (status, canonicals, titles, H1, links, hreflang, crawler access).
    - Sitemap updated; resubmit in Search Console and request indexing for new URLs if needed.
11. **Log** in `clients/<domain>/log.md`: date, department, what changed, branch/PR, verification result (status, PageSpeed numbers).

## 4. Rollback
| Situation | Do |
|---|---|
| Problem found on the preview | Fix on the branch, or close the PR. Nothing is live. |
| Problem live after merge | Owner reverts the merge (GitHub "Revert" button on the PR, which opens a revert PR) or rolls back to the previous deploy in the host (Netlify: Deploys > earlier deploy > Publish deploy). Then fix on a new branch. |
| Live site down / broken forms | Roll back the deploy first, investigate second. Tell the owner immediately. |
| Database change went wrong | Owner restores from their backup; Claude only provides SQL and steps. |

Why one topic per branch: a revert removes only that change.

## 5. Common traps (seen on the first client)
- Bigger JavaScript bundles quietly hurt LCP: check build output size and PageSpeed after merges that add content to a JS app.
- A build can fail on the host when an external service (database, API) is down or paused; the error is not in the change itself. Check the service first.
- Font swap causes layout shift (CLS); preload the main font weight.
- Old URLs need 301s in the host config when slugs change; avoid redirect chains.

## 6. Client on a CMS without code access
Claude does not log into client CMSs or enter passwords. Deliver exact steps instead:

1. Read the platform section in `platforms.md`.
2. Write a numbered click path per change: menu > page > field, and the **exact text to paste** (title, meta description, JSON-LD block, redirect rows from -> to, alt text).
3. One change set per message/file, in priority order; save it as `clients/<domain>/reports/<date>-<topic>-steps.md`.
4. Ask the owner for a screenshot if the admin screen is unknown.
5. After the owner says it is done: verify live exactly as in step 10 above, then log.

## Checklist
- [ ] Read `client.json` + platform section
- [ ] Branch per change, from up-to-date live branch
- [ ] Build passes; SEO checks pass
- [ ] Preview desktop + mobile, all languages
- [ ] Clear commit message; no secrets committed
- [ ] Owner OK before push; owner reviews hosting preview and merges
- [ ] Live: 200s, change in server HTML, PageSpeed before/after, tech_audit for big changes
- [ ] Sitemap / indexing handled
- [ ] `log.md` updated

## Worked example: reservella.net
React + Vite on Netlify behind Cloudflare. Every change went on its own branch (`site-audit-fixes`, `internal-links`, `arabic-phase-a`, `arabic-code-split`...), passed the build and `check:seo`, was pushed, reviewed by the owner on the Netlify preview and merged as a PR (#4 to #16). After merges Claude checked live status and PageSpeed; after PR #13 that caught a hotel-page LCP regression, fixed by PR #14. Cloudflare bot rules, Supabase SQL and Admin edits were done by the owner from Claude's steps. Details: `clients/reservella.net/log.md`.
