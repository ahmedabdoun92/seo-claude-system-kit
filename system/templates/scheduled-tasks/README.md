# Scheduled-task templates

One file per loop. When a client is onboarded (skill section 4g), Claude copies each template, replaces the placeholders and creates a scheduled task with the cron shown.

| Placeholder | Example |
|---|---|
| `{{DOMAIN}}` | example.com (the client folder name) |
| `{{SITE_URL}}` | https://www.example.com |
| `{{BRAND}}` | Example Co |
| `{{HOME_SCS}}` | the full path of this SEO Claude System folder |

| Template | Task name | Cron (local time) |
|---|---|---|
| weekly-report.md | `<client>-weekly-seo-report` | `0 9 * * 1` (Monday 09:00) |
| monthly-tech-audit.md | `<client>-monthly-tech-audit` | `0 9 1 * *` (1st, 09:00) |
| ai-visibility.md | `<client>-ai-visibility` | `0 10 17 * *` (17th, 10:00) |
| client-report.md | `<client>-client-report` | `0 10 3 * *` (3rd, 10:00) |

Scheduled tasks run in the Claude desktop app (Code tab → Scheduled). With the Claude Code CLI only, run the same prompts by hand or from your own scheduler (cron, Task Scheduler) with `claude -p "<prompt>"`.
