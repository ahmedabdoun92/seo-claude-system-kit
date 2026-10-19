Monthly AI-search visibility round for the client {{DOMAIN}} ({{BRAND}}) in the SEO Claude System (home {{HOME_SCS}}). Read {{HOME_SCS}}/CLAUDE.md and section 7 "AI visibility" of the seo-claude-system skill, then follow it:

1. Read clients/{{DOMAIN}}/questions.md (all approved customer questions, every language) and client.json.
2. Sample one AI web-search answer per question with parallel agents (about 8–9 questions each). Per question: id, question, lang, cited_domains, client_cited, client_mentioned (true only if the answer names {{BRAND}} on its own), brands_mentioned, answer_gist, answer_quality (good|weak|none). Retry a rate-limited question once.
3. Save the parts in clients/{{DOMAIN}}/data/_ai-round/<today>/ and merge them into round-<today>.json (check every id is present).
4. Run: python "{{HOME_SCS}}/system/scripts/ai_visibility.py" {{DOMAIN}} <round.json> --json (compares with the last round, writes reports/ai-visibility-<date>.md).
5. Add to the report: what changed since last month, remaining weak or empty answers, and 3–5 actions. Add a line to log.md.
6. Reply: cited X of N (was Y), mentions, biggest change, top 3 actions, report path. Do not change the website or contact anyone.
