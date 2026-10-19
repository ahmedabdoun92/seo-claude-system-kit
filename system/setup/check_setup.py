#!/usr/bin/env python3
"""Check every free data source the SEO Claude System uses.

Usage:
    python check_setup.py                    # all tools
    python check_setup.py --client example.com
    python check_setup.py --json             # machine-readable, for Claude

Moz is never live-checked here, so the small free monthly quota is kept for
real work. Keys are never printed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BACKLINKS_CONFIG, CLIENTS_DIR, GOOGLE_CONFIG, google_error, http_json,
    load_json, normalize_domain, run_seo_script,
)

BING_API = "https://ssl.bing.com/webmaster/api.svc/json"
OPR_API = "https://openpagerank.keywordseverywhere.com/v1/domains/bulk"
CRUX_API = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
PSI_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
TRANCO_API = "https://tranco-list.eu/api/ranks/domain/"


def result(ok, detail, needed_for, fix=""):
    return {"ok": ok, "detail": detail, "needed_for": needed_for, "fix": fix}


# ---------- individual checks (also imported by setup_keys.py) ----------

def check_service_account() -> tuple[dict, list]:
    cfg = load_json(GOOGLE_CONFIG)
    sa_path = cfg.get("service_account_path")
    if not sa_path or not os.path.exists(sa_path):
        return result(False, "No service account file configured",
                      "Search Console, GA4, URL inspection",
                      "Run /seo google setup"), []
    email = load_json(Path(sa_path)).get("client_email", "?")
    code, out = run_seo_script("gsc_query.py", "sites", "--json")
    if isinstance(out, dict) and not out.get("error"):
        sites = [s.get("url") for s in out.get("sites", [])]
        return result(True, f"{email} can read {len(sites)} Search Console site(s)",
                      "Search Console, GA4, URL inspection"), sites
    return result(False, f"{email}: {str(out)[:200]}", "Search Console, GA4, URL inspection",
                  "Check the service account file and that the Search Console API is enabled"), []


def service_account_email() -> str:
    sa_path = load_json(GOOGLE_CONFIG).get("service_account_path")
    return load_json(Path(sa_path)).get("client_email", "") if sa_path else ""


def check_crux(key: str, origin: str = "https://www.google.com") -> tuple[bool, str, dict | None]:
    code, out = http_json(f"{CRUX_API}?key={key}", "POST", {"origin": origin})
    if code == 200:
        return True, "Chrome UX Report API works", out
    if code == 404:
        return True, "Chrome UX Report API works (no field data for this origin)", None
    return False, f"Chrome UX Report API error {code}: {google_error(out)}", None


def check_psi(key: str) -> tuple[bool, str]:
    url = f"{PSI_API}?url=https://example.com/&strategy=mobile&category=performance&key={key}"
    code, out = http_json(url, timeout=120)
    if code == 200:
        return True, "PageSpeed Insights API works"
    return False, f"PageSpeed Insights API error {code}: {google_error(out)}"


def masked_env_google_key() -> bool:
    """True when GOOGLE_API_KEY holds the console's masked display (AIza....) instead of a key."""
    v = os.environ.get("GOOGLE_API_KEY", "")
    return bool(v) and not v.isascii()


def check_google_api_key(full: bool = True) -> dict:
    key = load_json(GOOGLE_CONFIG).get("api_key") or os.environ.get("GOOGLE_API_KEY")
    needed = "PageSpeed (lab speed tests), CrUX (real-user Core Web Vitals, competitor traffic signal)"
    if key and not key.isascii():
        return result(False, "The Windows GOOGLE_API_KEY variable holds a masked copy (AIza....), "
                      "not a real key", needed,
                      "Run setup_keys.py (step 1) to save the real key; then delete the variable")
    if not key:
        return result(False, "Missing. PageSpeed returns 429 without a key; CrUX needs one",
                      needed, "Run setup_keys.py (step 1)")
    ok_crux, msg_crux, _ = check_crux(key)
    msgs, ok = [msg_crux], ok_crux
    if full:
        ok_psi, msg_psi = check_psi(key)
        msgs.append(msg_psi)
        ok = ok and ok_psi
    fix = "" if ok else "Enable the failing API in Google Cloud > APIs & Services > Library"
    return result(ok, "; ".join(msgs), needed, fix)


def bing_sites(key: str) -> tuple[int, list | str]:
    code, out = http_json(f"{BING_API}/GetUserSites?apikey={key}")
    if code == 200 and isinstance(out, dict):
        return code, [
            {"url": s.get("Url"), "verified": bool(s.get("IsVerified"))}
            for s in (out.get("d") or [])
        ]
    msg = out.get("Message") if isinstance(out, dict) else str(out)
    return code, str(msg)[:200]


def check_bing() -> tuple[dict, list]:
    key = load_json(BACKLINKS_CONFIG).get("bing_api_key") or os.environ.get("BING_WEBMASTER_API_KEY")
    needed = "Keyword volumes (Bing keyword research), Bing backlinks, Bing/Copilot search data, IndexNow"
    if not key:
        return result(False, "Missing", needed, "Run setup_keys.py (step 2)"), []
    code, sites = bing_sites(key)
    if isinstance(sites, list):
        verified = [s["url"] for s in sites if s["verified"]]
        return result(True, f"Works; {len(verified)} verified site(s) of {len(sites)}", needed), sites
    return result(False, f"Bing API error {code}: {sites}", needed,
                  "Re-copy the key from Bing Webmaster Tools > Settings > API access"), []


def check_opr(key: str | None = None) -> dict:
    key = key or load_json(BACKLINKS_CONFIG).get("keywordseverywhere_api_key") \
        or os.environ.get("KEYWORDSEVERYWHERE_API_KEY")
    needed = "Competitor numbers: Open PageRank score (0-10) and referring domains"
    if not key:
        return result(False, "Missing (optional but recommended)", needed, "Run setup_keys.py (step 3)")
    code, out = http_json(OPR_API, "POST", {"domains": ["google.com"], "include_history": False},
                          {"Authorization": f"Bearer {key.strip()}"})
    if code == 200 and isinstance(out, dict) and out.get("results"):
        return result(True, "Works", needed)
    detail = out.get("error") or out.get("message") if isinstance(out, dict) else str(out)
    return result(False, f"Open PageRank error {code}: {str(detail)[:200]}", needed,
                  "Use the free OPR key (starts with opr_live_)")


def check_moz() -> dict:
    key = load_json(BACKLINKS_CONFIG).get("moz_api_key") or os.environ.get("MOZ_API_KEY")
    needed = "Competitor numbers: Moz Domain Authority (optional)"
    if not key:
        return result(False, "Missing (optional)", needed, "Run setup_keys.py (step 4)")
    return result(True, "Saved (not live-checked, to keep the free monthly quota)", needed)


def check_tranco() -> dict:
    code, out = http_json(TRANCO_API + "google.com")
    ok = code == 200 and isinstance(out, dict) and bool(out.get("ranks"))
    return result(ok, "Works (no key needed)" if ok else f"Tranco error {code}",
                  "Competitor numbers: global popularity rank")


def check_ga4(property_id: str) -> dict:
    code, out = run_seo_script("ga4_report.py", "--property", str(property_id),
                               "--days", "7", "--report", "organic", "--json")
    if code == 0 and isinstance(out, dict) and not out.get("error"):
        return result(True, f"GA4 property {property_id} readable", "Traffic and conversion reports")
    err = out.get("error") if isinstance(out, dict) else out
    return result(False, f"GA4 property {property_id}: {str(err)[:200]}", "Traffic and conversion reports",
                  f"In GA4 > Admin > Property access management, add {service_account_email()} as Viewer")


# ---------- client-level check ----------

def match_gsc_property(domain: str, sites: list) -> str | None:
    wanted = [f"sc-domain:{domain}", f"https://{domain}/", f"https://www.{domain}/",
              f"http://{domain}/", f"http://www.{domain}/"]
    for w in wanted:
        if w in sites:
            return w
    return None


def check_client(domain: str, gsc_sites: list, bing_list: list) -> dict:
    domain = normalize_domain(domain)
    client_file = CLIENTS_DIR / domain / "client.json"
    client = load_json(client_file)
    email = service_account_email()
    out = {"domain": domain, "client_folder_exists": (CLIENTS_DIR / domain).exists()}

    prop = match_gsc_property(domain, gsc_sites)
    out["search_console"] = result(
        bool(prop), f"Property {prop}" if prop else "Not visible to the service account",
        "Rankings, clicks, decay, indexing",
        "" if prop else f"Search Console > Settings > Users and permissions > Add user: {email} (Full)")
    out["gsc_property"] = prop

    ga4_id = client.get("ga4_property_id")
    out["ga4"] = check_ga4(ga4_id) if ga4_id else result(
        False, "No GA4 property ID saved for this client", "Traffic and conversion reports",
        f"Add {email} as Viewer in GA4, then give Claude the numeric property ID")

    bing_match = [s for s in bing_list if normalize_domain(s["url"] or "") == domain]
    out["bing"] = result(
        bool(bing_match and bing_match[0]["verified"]),
        "Verified in Bing Webmaster Tools" if bing_match and bing_match[0]["verified"]
        else ("Added but not verified" if bing_match else "Not in your Bing Webmaster Tools account"),
        "Bing keyword data and Bing search performance for this site",
        "" if bing_match and bing_match[0]["verified"]
        else "Bing Webmaster Tools > Add site > Import from Google Search Console")
    return out


# ---------- report ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", help="Also check access for this client domain")
    ap.add_argument("--quick", action="store_true", help="Skip the slow PageSpeed test")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sa, gsc_sites = check_service_account()
    bing, bing_list = check_bing()
    report = {
        "tools": {
            "google_service_account": sa,
            "google_api_key": check_google_api_key(full=not args.quick),
            "bing_webmaster": bing,
            "open_pagerank": check_opr(),
            "moz": check_moz(),
            "tranco": check_tranco(),
        },
        "masked_google_env_var": masked_env_google_key(),
        "service_account_email": service_account_email(),
        "search_console_sites": gsc_sites,
        "bing_sites": bing_list,
    }
    if args.client:
        report["client"] = check_client(args.client, gsc_sites, bing_list)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("\nSEO Claude System - setup check\n")
    for name, r in report["tools"].items():
        mark = "OK " if r["ok"] else "-- "
        print(f"  [{mark}] {name:24} {r['detail']}")
        if not r["ok"] and r["fix"]:
            print(f"         fix: {r['fix']}")
    if report["masked_google_env_var"] and load_json(GOOGLE_CONFIG).get("api_key"):
        print("\n  Note: the Windows GOOGLE_API_KEY variable still holds a masked key (AIza....).")
        print("  The saved real key is used instead, but delete the variable to avoid confusion.")
    if gsc_sites:
        print("\n  Search Console sites:", ", ".join(gsc_sites))
    if args.client:
        c = report["client"]
        print(f"\n  Client {c['domain']}:")
        for k in ("search_console", "ga4", "bing"):
            r = c[k]
            print(f"  [{'OK ' if r['ok'] else '-- '}] {k:24} {r['detail']}")
            if not r["ok"] and r["fix"]:
                print(f"         fix: {r['fix']}")
    print()


if __name__ == "__main__":
    main()
