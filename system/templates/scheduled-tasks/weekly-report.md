Run the SEO Claude System weekly report for the client {{DOMAIN}} and summarise it.

The SEO Claude System lives in {{HOME_SCS}}. Read its CLAUDE.md first (free tools only, never invent facts, never print API keys). The client folder is {{HOME_SCS}}/clients/{{DOMAIN}}.

1. Run: python "{{HOME_SCS}}/system/scripts/weekly_report.py" {{DOMAIN}} --json
   It takes about 5 seconds per sitemap URL (it re-checks every URL in Google). Use a timeout of at least 15 minutes. Use --no-inspect only if the full run fails twice, and say so.
2. The script writes reports/weekly-<today>.md, saves snapshots and adds a line to log.md. Do not edit those files or the client's website.
3. Reply in plain words: clicks, impressions, pages indexed and conversions vs last week; anything urgent (pages that dropped out of the index, decaying pages, form or booking errors); newly indexed pages; the top 3 actions from "What to do this week"; open owner tasks; the report path.
4. If the script fails, report the exact error and the likely fix. Do not change any configuration.
