"""Fast health check of the whole SEO Claude System (no paid or rate-limited APIs).

Usage:
  python system/tests/smoke.py

Checks:
  1. every .py in system/scripts and system/setup compiles (py_compile)
  2. each argparse script answers --help with exit 0 (30 s timeout; GA4/Google
     scripts run with the claude-seo .venv python); scripts
     without argparse (they would run for real) and library modules are skipped
  3. client templates exist and template client.json is valid JSON
  4. check_client.py --all runs (exit 0 or 1; a crash is a failure)
  5. CLAUDE.md and system/reference/departments.md exist, and departments.md has
     50 role rows, each with status ready|partial|planned
Prints a summary table and exits 1 if anything fails.
"""

import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path(__file__).resolve().parents[2]
SYSTEM = HOME / "system"
SCRIPT_DIRS = [SYSTEM / "scripts", SYSTEM / "setup"]
TEMPLATE_FILES = ["client.json", "profile.md", "competitors.md", "questions.md", "log.md"]
STATUSES = {"ready", "partial", "planned"}
EXPECTED_ROLES = 50
HELP_TIMEOUT = 30
# Scripts that import the Google client libraries must run with the claude-seo virtual environment.
SEO_VENV_PY = Path(os.path.expanduser("~/.claude/skills/seo/.venv/Scripts/python.exe"))
if not SEO_VENV_PY.exists():
    SEO_VENV_PY = Path(os.path.expanduser("~/.claude/skills/seo/.venv/bin/python"))

# Never run these with --help: they ignore it and would do real work, or need the network on import.
NO_HELP = {
    "common.py": "library module",
    "backup.py": "no argparse; would commit/push",
    "sync_claude_files.py": "no argparse; would copy files",
}

results: list[tuple[str, str, str, str]] = []   # (group, item, status, detail)


def add(group, item, status, detail=""):
    results.append((group, item, status, detail))


def py_files():
    for d in SCRIPT_DIRS:
        if d.is_dir():
            yield from sorted(p for p in d.glob("*.py") if p.is_file())


def check_compile():
    tmp = Path(tempfile.mkdtemp(prefix="seo-smoke-"))
    for p in py_files():
        rel = p.relative_to(HOME).as_posix()
        try:
            py_compile.compile(str(p), cfile=str(tmp / (p.stem + ".pyc")), doraise=True)
            add("compile", rel, "PASS")
        except py_compile.PyCompileError as exc:
            msg = str(exc).strip().splitlines()[-1] if str(exc).strip() else "compile error"
            add("compile", rel, "FAIL", msg[:120])


def check_help():
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    for p in py_files():
        rel = p.relative_to(HOME).as_posix()
        if p.name in NO_HELP:
            add("--help", rel, "SKIP", NO_HELP[p.name])
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            add("--help", rel, "FAIL", f"cannot read: {exc}")
            continue
        if "argparse" not in src or "__main__" not in src:
            add("--help", rel, "SKIP", "no argparse entry point")
            continue
        python = sys.executable
        if "claude-seo .venv" in src or re.search(r"^\s*from google\.", src, re.M):
            if not SEO_VENV_PY.exists():
                add("--help", rel, "SKIP", "needs the claude-seo .venv python (not found)")
                continue
            python = str(SEO_VENV_PY)
        t0 = time.time()
        try:
            proc = subprocess.run([python, str(p), "--help"], cwd=str(HOME), env=env,
                                  stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=HELP_TIMEOUT)
        except subprocess.TimeoutExpired:
            add("--help", rel, "FAIL", f"timed out after {HELP_TIMEOUT}s")
            continue
        secs = f"{time.time() - t0:.1f}s"
        if proc.returncode == 0:
            add("--help", rel, "PASS", secs + (" (claude-seo .venv)" if python != sys.executable else ""))
        else:
            err = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
            add("--help", rel, "FAIL", f"exit {proc.returncode}: {err[-1][:100] if err else ''}")


def check_templates():
    tdir = SYSTEM / "templates" / "client"
    for name in TEMPLATE_FILES:
        p = tdir / name
        if not p.is_file():
            add("templates", f"templates/client/{name}", "FAIL", "missing")
            continue
        if name.endswith(".json"):
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                add("templates", f"templates/client/{name}", "FAIL", f"invalid JSON: {exc}")
                continue
        add("templates", f"templates/client/{name}", "PASS")


def check_clients():
    script = SYSTEM / "setup" / "check_client.py"
    if not script.is_file():
        add("clients", "check_client.py --all", "FAIL", "script missing")
        return
    try:
        proc = subprocess.run([sys.executable, str(script), "--all"], cwd=str(HOME),
                              env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"),
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        add("clients", "check_client.py --all", "FAIL", "timed out")
        return
    out = proc.stdout
    if "No client folders" in out + proc.stderr:
        add("clients", "check_client.py --all", "SKIP", "no clients yet (fresh install)")
        return
    if proc.returncode not in (0, 1) or "Overall:" not in out:
        err = (proc.stderr.strip() or out.strip()).splitlines()
        add("clients", "check_client.py --all", "FAIL", f"crashed (exit {proc.returncode}): {err[-1][:100] if err else ''}")
        return
    for m in re.finditer(r"=== (.+?) ===.*?-> (\d+) pass, (\d+) warn, (\d+) fail", out, re.S):
        dom, p, w, f = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        status = "FAIL" if f else ("WARN" if w else "PASS")
        add("clients", dom, status, f"{p} pass, {w} warn, {f} fail")
    add("clients", "check_client.py --all", "PASS", out.strip().splitlines()[-1])


def check_docs():
    claude = HOME / "CLAUDE.md"
    add("docs", "CLAUDE.md", "PASS" if claude.is_file() else "FAIL", "" if claude.is_file() else "missing")
    dep = SYSTEM / "reference" / "departments.md"
    if not dep.is_file():
        add("docs", "system/reference/departments.md", "FAIL", "missing")
        return
    add("docs", "system/reference/departments.md", "PASS")
    rows, bad, in_roles = [], [], False
    for line in dep.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            in_roles = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() == "role" and cells[1].lower() == "status":
            in_roles = True
            continue
        if not in_roles or set(s) <= set("|-: "):
            continue
        if len(cells) >= 2 and cells[1].lower() in STATUSES:
            rows.append((cells[0], cells[1].lower()))
        else:
            bad.append(cells[0])
    counts = {s: sum(1 for _, st in rows if st == s) for s in sorted(STATUSES)}
    detail = f"{len(rows)} roles ({', '.join(f'{k} {v}' for k, v in counts.items())})"
    if bad:
        add("docs", "departments.md statuses", "FAIL", f"bad status on: {', '.join(bad[:5])}")
    if len(rows) != EXPECTED_ROLES:
        add("docs", "departments.md role rows", "FAIL", f"{detail}; expected {EXPECTED_ROLES}")
    else:
        add("docs", "departments.md role rows", "PASS", detail)


def main() -> int:
    t0 = time.time()
    check_compile()
    check_help()
    check_templates()
    check_clients()
    check_docs()

    w_group = max(len(r[0]) for r in results)
    w_item = max(len(r[1]) for r in results)
    print(f"{'GROUP':<{w_group}}  {'ITEM':<{w_item}}  STATUS  DETAIL")
    print("-" * (w_group + w_item + 24))
    for g, item, st, detail in results:
        print(f"{g:<{w_group}}  {item:<{w_item}}  {st:<6}  {detail}")
    fails = [r for r in results if r[2] == "FAIL"]
    summary = {s: sum(1 for r in results if r[2] == s) for s in ("PASS", "WARN", "SKIP", "FAIL")}
    print("-" * (w_group + w_item + 24))
    print("Summary: " + ", ".join(f"{v} {k.lower()}" for k, v in summary.items()) + f" in {time.time() - t0:.1f}s")
    print("SMOKE TEST: " + ("FAILED" if fails else "PASSED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
