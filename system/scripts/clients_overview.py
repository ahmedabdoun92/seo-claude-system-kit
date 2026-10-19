#!/usr/bin/env python3
"""One table for every client: latest numbers, health and what is waiting.

For each folder in clients/ it reads the newest weekly Search Console snapshot (and the one before),
indexing snapshot, technical check, AI-visibility round and todo.md, and prints:
clicks and impressions (last week vs the week before), pages indexed, open technical problems,
AI-visibility citations, dates of the latest reports and open owner tasks.

Usage:
    python clients_overview.py            # table in the terminal
    python clients_overview.py --md       # also write system/reference/clients-overview.md
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import CLIENTS_DIR, load_json  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def latest(folder: Path, pattern: str) -> list[Path]:
    return sorted(folder.glob(pattern))


def week_totals(path: Path) -> tuple[int, int]:
    d = load_json(path)
    rows = d.get("rows") or d.get("query_page") or d.get("pages") or []
    if isinstance(d.get("totals"), dict):
        t = d["totals"]
        return int(t.get("clicks", 0)), int(t.get("impressions", 0))
    clicks = sum(int(r.get("clicks", 0)) for r in rows if isinstance(r, dict))
    impr = sum(int(r.get("impressions", 0)) for r in rows if isinstance(r, dict))
    return clicks, impr


def open_tasks(todo: Path, section: str) -> int:
    if not todo.exists():
        return 0
    text = todo.read_text(encoding="utf-8")
    m = re.search(rf"^## {section}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return len(re.findall(r"^- \[ \]", m.group(1), re.M)) if m else 0


def row(folder: Path) -> dict:
    r = {"client": folder.name}
    weeks = latest(folder / "snapshots", "gsc-week-*.json")
    if weeks:
        c, i = week_totals(weeks[-1])
        r["week"] = weeks[-1].stem.replace("gsc-week-", "")
        r["clicks"], r["impressions"] = c, i
        if len(weeks) > 1:
            pc, pi = week_totals(weeks[-2])
            r["prev"] = f"{pc} / {pi}"
    idx = latest(folder / "snapshots", "index-*.json")
    if idx:
        states = load_json(idx[-1]).get("index", {})
        r["indexed"] = f"{sum(1 for s in states.values() if str(s).startswith('Submitted and indexed'))}/{len(states)}"
    tech = latest(folder / "data", "tech-audit-*.json")
    if tech:
        r["tech_problems"] = len(load_json(tech[-1]).get("issues", []))
        r["tech_date"] = tech[-1].stem.replace("tech-audit-", "")
    ai = latest(folder / "data", "ai-visibility-*.json")
    if ai:
        s = load_json(ai[-1]).get("score", {})
        r["ai_cited"] = f"{s.get('client_cited', 0)}/{s.get('questions', 0)}"
        r["ai_date"] = ai[-1].stem.replace("ai-visibility-", "")
    reports = latest(folder / "reports", "weekly-*.md")
    if reports:
        r["weekly_date"] = reports[-1].stem.replace("weekly-", "")
    r["owner_tasks"] = open_tasks(folder / "todo.md", "Owner")
    r["waiting"] = open_tasks(folder / "todo.md", "Waiting")
    return r


COLS = [("client", "Client"), ("week", "GSC week to"), ("clicks", "Clicks"), ("impressions", "Impr."), ("prev", "Prev wk (clk/impr)"),
        ("indexed", "Indexed"), ("tech_problems", "Tech problems"), ("ai_cited", "AI cited"), ("weekly_date", "Last weekly"),
        ("tech_date", "Last tech check"), ("ai_date", "Last AI round"), ("owner_tasks", "Owner tasks"), ("waiting", "Waiting")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = [row(f) for f in sorted(CLIENTS_DIR.iterdir()) if f.is_dir() and (f / "client.json").exists()]
    if a.json:
        print(json.dumps(rows, indent=1))
        return
    lines = ["| " + " | ".join(h for _, h in COLS) + " |", "|" + "---|" * len(COLS)]
    lines += ["| " + " | ".join(str(r.get(k, "–")) for k, _ in COLS) + " |" for r in rows]
    table = "\n".join(lines)
    print(table)
    if a.md:
        out = ROOT / "system" / "reference" / "clients-overview.md"
        out.write_text(f"# Clients overview\n\nGenerated {dt.date.today().isoformat()} by `system/scripts/clients_overview.py`.\n\n{table}\n", encoding="utf-8")
        print(f"\nwritten {out}")


if __name__ == "__main__":
    main()
