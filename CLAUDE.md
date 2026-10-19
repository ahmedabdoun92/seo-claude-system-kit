# SEO Claude System

A reusable, multi-client SEO department (10 departments × 5 roles) run by Claude Code.
Entry point: the `seo-claude-system` skill. Start it by saying **"SEO Claude System"**.

## Folder map
```
CLAUDE.md                      this file: house rules
clients/<domain>/              one folder per client site (private: never commit to a public repo)
  client.json                  machine fields: platform, markets, languages, gsc_property, ga4_property_id, onboarding flags
  profile.md                   business profile (only facts the user gave)
  competitors.md               3-5 big competitors with numbers + SERP rivals
  questions.md                 20-50 customer questions (Google / ChatGPT)
  todo.md                      open tasks: Owner / Claude / Waiting
  log.md                       work log, newest first
  data/ reports/ snapshots/ content/
system/setup/                  check_setup.py, setup_keys.py, check_client.py, backup.py, common.py
system/scripts/                weekly_report.py, tech_audit.py, ai_visibility.py, client_report.py, …
system/templates/              files copied into each new client folder; scheduled-task prompts
system/reference/              departments.md (routing + status), platforms.md (per-CMS how-to), playbooks
system/tests/smoke.py          self-test
```

## House rules
- **Free tools only.** Never use, suggest or ask for paid APIs (Semrush, Ahrefs, DataForSEO, Profound, paid keyword or backlink databases…). If a job needs a paid tool, skip it and say what was skipped.
- **Ask, don't invent.** Business facts come from the user. Unknown = `TBD`. Numbers come from a named source with a date.
- **One client at a time.** Always know which `clients/<domain>/` you're working in; read `client.json` and `profile.md` first. Pass the client's own `--property` to every Search Console / GA4 call.
- **Platform-specific advice.** Read the client's section in `system/reference/platforms.md` before recommending fixes.
- **Status honesty.** `system/reference/departments.md` says which roles are ready, partial or planned. Never pretend a planned role ran.
- **Keys never in chat.** API keys are saved with `python system/setup/setup_keys.py` in the user's own terminal. Never ask the user to paste a key into the chat, never print one.
- **No sending.** Outreach, PR pitches, client reports and expert-quote requests are drafts; the user sends them.
- **Site changes are reviewed.** Code changes go on a branch with a preview; the owner merges.
- **Log everything.** After each piece of work add a line to the client's `log.md`, update `todo.md`, and save outputs in that client's folders.
- Run Python with `python` (3.10+). Bundled claude-seo tools run via `bash "$HOME/.claude/skills/seo/scripts/claude-seo" run <script>.py ...`.
