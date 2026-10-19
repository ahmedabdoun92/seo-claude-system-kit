"""Check that a client folder matches what the SEO Claude System expects.

Usage:
  python system/setup/check_client.py example.com
  python system/setup/check_client.py --all

Checks: required files and folders, client.json fields and types, TBD gaps in
profile.md, how fresh the weekly report / tech audit / AI-visibility round are,
and which scheduled-task loops exist in %USERPROFILE%\\.claude\\scheduled-tasks.
Prints PASS / WARN / FAIL (and INFO) lines with a fix for each problem.
Exit code 1 if any FAIL. Standard library only; no network calls.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HOME_DIR, CLIENTS_DIR, normalize_domain  # noqa: E402

SCHEDULED_DIR = Path(os.path.expanduser("~/.claude/scheduled-tasks"))

REQUIRED_FILES = ["client.json", "profile.md", "competitors.md", "questions.md", "log.md"]
REQUIRED_DIRS = ["data", "reports", "snapshots", "content"]
ONBOARDING_FLAGS = ["profile", "access_checked", "competitors", "questions"]

# name, report filename prefix, max age in days, script, cron, folder-name keywords
LOOPS = [
    ("weekly report", "weekly-", 8, "weekly_report.py", "0 9 * * 1", ("weekly",)),
    ("monthly tech audit", "tech-audit-", 35, "tech_audit.py", "0 9 1 * *", ("tech-audit", "tech_audit")),
    ("AI visibility", "ai-visibility-", 40, "ai_visibility.py", "0 10 17 * *", ("ai-visibility", "ai_visibility")),
]

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


class Result:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []

    def add(self, level: str, msg: str, fix: str = ""):
        self.rows.append((level, msg, fix))

    def count(self, level: str) -> int:
        return sum(1 for r in self.rows if r[0] == level)


def check_files(folder: Path, r: Result):
    for name in REQUIRED_FILES:
        if (folder / name).is_file():
            r.add("PASS", f"{name} exists")
        else:
            src = Path("system/templates/client") / name
            r.add("FAIL", f"{name} missing", f"copy {src.as_posix()} into the client folder and fill it in")
    if (folder / "todo.md").is_file():
        r.add("PASS", "todo.md exists")
    else:
        r.add("WARN", "todo.md missing", "create todo.md with the open tasks for this client (one '- [ ]' line each)")
    for name in REQUIRED_DIRS:
        if (folder / name).is_dir():
            r.add("PASS", f"{name}/ folder exists")
        else:
            r.add("FAIL", f"{name}/ folder missing", f"create the folder clients/{folder.name}/{name}/")


def _is_str_list(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def check_client_json(folder: Path, r: Result) -> dict:
    path = folder / "client.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        r.add("FAIL", f"client.json is not valid JSON ({exc})", "fix the JSON syntax (check commas and quotes)")
        return {}
    if not isinstance(data, dict):
        r.add("FAIL", "client.json is not a JSON object", "rebuild it from system/templates/client/client.json")
        return {}

    def bad(field, why, fix, level="FAIL"):
        r.add(level, f"client.json {field}: {why}", fix)

    # domain
    dom = data.get("domain")
    if not isinstance(dom, str) or not dom.strip():
        bad("domain", "missing", f'set "domain": "{folder.name}"')
    elif normalize_domain(dom) != folder.name.lower():
        bad("domain", f"'{dom}' does not match folder name '{folder.name}'", "make the domain and the folder name the same")
    else:
        r.add("PASS", f"client.json domain = {dom}")

    for field, hint in (("business_name", "the business name the user gave"),
                        ("platform", "the CMS/platform (see system/reference/platforms.md)")):
        v = data.get(field)
        if not isinstance(v, str) or not v.strip():
            bad(field, "missing or empty", f"ask the user for {hint} and set \"{field}\"")
        elif v.strip().upper() == "TBD":
            bad(field, "is TBD", f"ask the user for {hint}", "WARN")
        else:
            r.add("PASS", f"client.json {field} set")

    ch = data.get("canonical_host")
    if ch is None or ch == "":
        bad("canonical_host", "missing", 'set "canonical_host": "https://www.<domain>" (the host the site redirects to)', "WARN")
    elif not isinstance(ch, str) or not re.fullmatch(r"https://[a-z0-9.-]+\.[a-z]{2,}/?", ch.strip().lower()):
        bad("canonical_host", f"'{ch}' is not an https:// host URL", 'use the form "https://www.example.com"')
    else:
        r.add("PASS", f"client.json canonical_host = {ch}")

    gsc = data.get("gsc_property")
    if not gsc:
        bad("gsc_property", "missing", 'add the Search Console property, e.g. "sc-domain:example.com" (run check_setup.py)', "WARN")
    elif not isinstance(gsc, str) or not (re.fullmatch(r"sc-domain:[a-z0-9.-]+\.[a-z]{2,}", gsc)
                                          or re.fullmatch(r"https?://[^\s/]+/?.*", gsc)):
        bad("gsc_property", f"'{gsc}' is not sc-domain:<domain> or a URL prefix", 'use "sc-domain:example.com" or "https://www.example.com/"')
    else:
        r.add("PASS", f"client.json gsc_property = {gsc}")

    ga4 = data.get("ga4_property_id")
    if not ga4:
        bad("ga4_property_id", "missing", 'add "properties/<digits>" from GA4 Admin > Property details', "WARN")
    elif not isinstance(ga4, str) or not re.fullmatch(r"properties/\d+", ga4):
        bad("ga4_property_id", f"'{ga4}' is not properties/<digits>", 'use the form "properties/123456789"')
    else:
        r.add("PASS", f"client.json ga4_property_id = {ga4}")

    langs = data.get("languages")
    if not _is_str_list(langs) or not langs:
        bad("languages", "must be a non-empty list of language codes", 'e.g. "languages": ["en", "ar"]')
    else:
        r.add("PASS", f"client.json languages = {', '.join(langs)}")

    ob = data.get("onboarding")
    if not isinstance(ob, dict):
        bad("onboarding", "missing or not an object", "add the onboarding block from system/templates/client/client.json")
    else:
        wrong = [k for k in ONBOARDING_FLAGS if not isinstance(ob.get(k), bool)]
        pending = [k for k in ONBOARDING_FLAGS if ob.get(k) is False]
        if wrong:
            bad("onboarding", f"flags missing or not true/false: {', '.join(wrong)}", "set each flag to true or false")
        elif pending:
            bad("onboarding", f"not finished: {', '.join(pending)}", "finish these onboarding steps in the seo-claude-system skill", "WARN")
        else:
            r.add("PASS", "client.json onboarding complete")

    # optional fields
    if "competitor_domains" in data:
        if _is_str_list(data["competitor_domains"]):
            r.add("PASS", f"client.json competitor_domains: {len(data['competitor_domains'])}")
        else:
            bad("competitor_domains", "must be a list of domain strings", 'e.g. ["rival1.com", "rival2.com"]')
    if "conversion_events" in data:
        if _is_str_list(data["conversion_events"]):
            r.add("PASS", f"client.json conversion_events: {len(data['conversion_events'])}")
        else:
            bad("conversion_events", "must be a list of GA4 event names", 'e.g. ["generate_lead", "whatsapp_click"]')
    if "monitor_urls" in data:
        mu = data["monitor_urls"]
        problems = []
        if not isinstance(mu, list):
            problems.append("not a list")
        else:
            for i, item in enumerate(mu):
                if not isinstance(item, dict):
                    problems.append(f"item {i} is not an object")
                    continue
                for k in ("name", "url", "expect"):
                    if k not in item:
                        problems.append(f"item {i} has no '{k}'")
                if "name" in item and not isinstance(item["name"], str):
                    problems.append(f"item {i} name is not text")
                if "url" in item and not (isinstance(item["url"], str) and item["url"].startswith(("http://", "https://"))):
                    problems.append(f"item {i} url is not an http(s) URL")
        if problems:
            bad("monitor_urls", "; ".join(problems[:5]), 'each item: {"name": "...", "url": "https://...", "expect": ...}')
        else:
            r.add("PASS", f"client.json monitor_urls: {len(mu)}")
    return data


def check_profile(folder: Path, r: Result):
    path = folder / "profile.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    fields = {}
    for line in text.splitlines():
        m = re.match(r"\s*[-*]\s*\*\*(.+?):?\*\*:?\s*(.*)", line)
        if m:
            fields[m.group(1).strip().rstrip(":")] = m.group(2).strip()
    critical = {"business name": ("Name", "Business name"), "platform": ("Platform",)}
    crit_tbd, crit_missing = [], []
    for label, keys in critical.items():
        val = next((fields[k] for k in keys if k in fields), None)
        if val is None:
            crit_missing.append(label)
        elif not val or re.search(r"\bTBD\b", val):
            crit_tbd.append(label)
    if crit_tbd:
        r.add("WARN", f"profile.md critical fields are TBD: {', '.join(crit_tbd)}", "ask the user and fill these in (never guess)")
    if crit_missing:
        r.add("WARN", f"profile.md has no line for: {', '.join(crit_missing)}", "add '- **Name:**' / '- **Platform:**' lines from the template")
    if not crit_tbd and not crit_missing:
        r.add("PASS", "profile.md business name and platform filled")
    other = [k for k, v in fields.items() if re.search(r"\bTBD\b", v) and k not in ("Name", "Business name", "Platform")]
    if other:
        r.add("INFO", f"profile.md other TBD fields ({len(other)}): {', '.join(other)}", "ask the user when relevant")


def latest_date(folder: Path, prefix: str) -> dt.date | None:
    best = None
    reports = folder / "reports"
    if not reports.is_dir():
        return None
    for p in reports.rglob(f"{prefix}*.md"):
        m = DATE_RE.search(p.name[len(prefix):])
        if not m:
            continue
        try:
            d = dt.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if best is None or d > best:
            best = d
    return best


def check_freshness(folder: Path, r: Result, today: dt.date):
    for name, prefix, max_age, script, _cron, _kw in LOOPS:
        d = latest_date(folder, prefix)
        cmd = f'python system/scripts/{script} {folder.name}'
        if d is None:
            r.add("WARN", f"no {name} yet (reports/{prefix}<date>.md)", f"run: {cmd}")
            continue
        age = (today - d).days
        if age > max_age:
            r.add("WARN", f"latest {name} is {d} ({age} days old, limit {max_age})", f"run: {cmd}")
        else:
            r.add("PASS", f"latest {name} {d} ({age} days old)")


def check_scheduled(folder: Path, r: Result):
    label = folder.name.split(".")[0].lower()
    if not SCHEDULED_DIR.is_dir():
        r.add("WARN", f"no scheduled-tasks folder at {SCHEDULED_DIR}", "create the loops below with the scheduled-tasks tool")
        tasks = []
    else:
        tasks = sorted(p for p in SCHEDULED_DIR.iterdir() if p.is_dir() and p.name.lower().startswith(label + "-"))
    if tasks:
        r.add("INFO", f"scheduled tasks for '{label}-': {', '.join(p.name for p in tasks)}")
    for name, _prefix, _age, script, cron, keywords in LOOPS:
        found = None
        for t in tasks:
            if any(k in t.name.lower() for k in keywords):
                found = t
                break
            skill = t / "SKILL.md"
            try:
                body = skill.read_text(encoding="utf-8", errors="replace") if skill.is_file() else ""
            except OSError:
                body = ""
            if any("python" in line and script in line for line in body.splitlines()):
                found = t
                break
        if found:
            r.add("PASS", f"{name} loop scheduled ({found.name})")
        else:
            r.add("WARN", f"{name} loop not scheduled",
                  f'create scheduled task "{label}-{script[:-3].replace("_", "-")}" with cron "{cron}" running '
                  f'python "{(HOME_DIR / "system" / "scripts" / script).as_posix()}" {folder.name}')


def check_one(domain: str, today: dt.date) -> Result:
    r = Result()
    folder = CLIENTS_DIR / domain
    if not folder.is_dir():
        r.add("FAIL", f"client folder clients/{domain}/ not found", f"run: python system/scripts/new_client.py {domain}")
        return r
    check_files(folder, r)
    check_client_json(folder, r)
    check_profile(folder, r)
    check_freshness(folder, r, today)
    check_scheduled(folder, r)
    return r


def print_result(domain: str, r: Result):
    print(f"\n=== {domain} ===")
    for level, msg, fix in r.rows:
        print(f"  [{level}] {msg}")
        if fix and level in ("WARN", "FAIL"):
            print(f"         fix: {fix}")
    print(f"  -> {r.count('PASS')} pass, {r.count('WARN')} warn, {r.count('FAIL')} fail")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domain", nargs="?", help="client domain (folder name under clients/)")
    ap.add_argument("--all", action="store_true", help="check every client folder")
    ap.add_argument("--today", help="pretend today is YYYY-MM-DD (for testing)")
    args = ap.parse_args()
    if not args.all and not args.domain:
        ap.error("give a domain or --all")
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    if args.all:
        domains = sorted(p.name for p in CLIENTS_DIR.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))) \
            if CLIENTS_DIR.is_dir() else []
        if not domains:
            print("No client folders found under clients/.")
            return 0
    else:
        domains = [normalize_domain(args.domain)]

    any_fail = False
    for d in domains:
        r = check_one(d, today)
        print_result(d, r)
        any_fail |= r.count("FAIL") > 0
    print(f"\nOverall: {'FAIL' if any_fail else 'OK'} ({len(domains)} client(s) checked)")
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
