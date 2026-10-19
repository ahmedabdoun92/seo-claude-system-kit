#!/usr/bin/env python3
"""Create or list client folders for the SEO Claude System.

Usage:
    python new_client.py example.com      # create clients/example.com/ from templates
    python new_client.py --list --json    # list clients and their onboarding status
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import CLIENTS_DIR, GOOGLE_CONFIG, TEMPLATES_DIR, load_json, normalize_domain  # noqa: E402

SUBFOLDERS = ["data", "reports", "snapshots", "content"]


def create(domain: str) -> dict:
    domain = normalize_domain(domain)
    if not domain or "." not in domain:
        return {"ok": False, "error": f"'{domain}' doesn't look like a domain"}
    target = CLIENTS_DIR / domain
    if target.exists():
        return {"ok": False, "error": "exists", "path": str(target)}

    today = datetime.date.today().isoformat()
    target.mkdir(parents=True)
    for sub in SUBFOLDERS:
        (target / sub).mkdir()
    for tpl in (TEMPLATES_DIR / "client").iterdir():
        text = tpl.read_text(encoding="utf-8").replace("{{domain}}", domain).replace("{{date}}", today)
        (target / tpl.name).write_text(text, encoding="utf-8")

    # The claude-seo default property may already be this client's: reuse its GA4 ID.
    google = load_json(GOOGLE_CONFIG)
    client = load_json(target / "client.json")
    if normalize_domain(str(google.get("default_property", "")).replace("sc-domain:", "")) == domain:
        client["gsc_property"] = google.get("default_property", "")
        client["ga4_property_id"] = str(google.get("ga4_property_id", ""))
        (target / "client.json").write_text(json.dumps(client, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(target), "prefilled_google": bool(client.get("gsc_property"))}


def list_clients() -> list:
    if not CLIENTS_DIR.exists():
        return []
    out = []
    for d in sorted(p for p in CLIENTS_DIR.iterdir() if p.is_dir()):
        c = load_json(d / "client.json")
        out.append({"domain": d.name, "business_name": c.get("business_name", ""),
                    "platform": c.get("platform", ""), "onboarding": c.get("onboarding", {})})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domain", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.list or not args.domain:
        clients = list_clients()
        if args.json:
            print(json.dumps(clients, indent=2))
        elif not clients:
            print("No clients yet.")
        else:
            for c in clients:
                done = [k for k, v in c["onboarding"].items() if v]
                print(f"{c['domain']:30} {c['business_name'] or '-':25} onboarding: {', '.join(done) or 'not started'}")
        return

    res = create(args.domain)
    print(json.dumps(res, indent=2) if args.json else
          (f"Created {res['path']}" if res["ok"] else f"Not created: {res['error']} {res.get('path', '')}"))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
