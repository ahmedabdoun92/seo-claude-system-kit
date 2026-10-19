# Platform notes

Read the section for the client's platform (from `client.json` → `platform`) before giving any fix.
Every recommendation must say **where to click or which file to edit on that platform**, not generic advice.

## Access modes
- **Claude edits:** only for a site whose code is in a local folder or git repo the user points to. Edit the files, show the diff, never deploy without a clear yes.
- **Recommendations only:** give step-by-step instructions for that platform's admin, with the exact text to paste (title, meta description, schema JSON-LD, redirect rows).
- Never log into a client's CMS or enter passwords. If browser help is needed, the user signs in first.

## WordPress (incl. WooCommerce)
- Titles/meta, canonical, noindex, sitemaps: the SEO plugin in use (Yoast, Rank Math, AIOSEO). Ask which one; settings differ.
- Schema: SEO plugin's schema settings, or a code snippet plugin for custom JSON-LD.
- Redirects: Rank Math/Yoast Premium redirect manager or the free "Redirection" plugin.
- Speed: caching plugin + image optimisation; check theme/page-builder bloat (Elementor, Divi).
- Watch for: "Discourage search engines" in Settings > Reading, duplicate tag/category archives, attachment pages.

## Shopify
- Titles/meta: each product/collection/page > "Search engine listing". Theme title templates in `theme.liquid`.
- Fixed URL prefixes (`/products/`, `/collections/`, `/pages/`) can't be changed.
- Redirects: Online Store > Navigation > URL redirects (or CSV import).
- `robots.txt` via `robots.txt.liquid`; sitemap is automatic at `/sitemap.xml`.
- Watch for: duplicate product URLs inside collections (`/collections/x/products/y`), app scripts slowing pages.

## Wix
- Titles/meta per page: page's SEO settings (SEO Basics). Site-wide patterns: SEO Settings.
- Redirects: SEO Settings > URL redirect manager. Structured data: page SEO settings > Advanced > structured data markup.
- Watch for: heavy pages from many apps and animations.

## Webflow
- Titles/meta: Page settings > SEO settings; CMS items use field bindings in the template's page settings.
- Redirects: Site settings > Publishing > 301 redirects. Custom code (schema) in page settings > custom code.
- Watch for: staging `webflow.io` domain being indexed.

## Squarespace
- Titles/meta: page settings > SEO; site-wide formats in Marketing > SEO.
- Redirects: Settings > Developer tools > URL mappings. Code injection for schema needs a Business plan or higher.

## Salla / Zid (Saudi and GCC stores)
- Product and category SEO fields (title, description, URL) are in each item's edit screen under SEO settings.
- Theme and code access is limited; schema and robots changes may need the platform's app store or support.
- Arabic and English URLs/titles: confirm which language the market searches in.

## Custom code (Next.js, React, Laravel, static, other)
- Titles/meta/canonical in the framework's head/metadata API; schema as JSON-LD in the page template.
- Check rendering: content must be in the server HTML, not only after JavaScript (`seo-technical` checks this).
- Redirects in the framework config, the web server (nginx/Apache), or the host (Vercel/Netlify/Cloudflare).

## Other / unknown
Ask the user for a screenshot of the admin's SEO settings screen, then give steps from what is visible.
