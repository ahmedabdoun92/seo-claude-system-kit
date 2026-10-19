#!/usr/bin/env python3
"""Save the free API keys the SEO Claude System needs.

Run it in a terminal and paste each key when asked. Keys are typed hidden,
checked live, and saved to the claude-seo config files in
~/.config/claude-seo/ (readable only by your Windows user). They never go
into the chat.

Usage:
    python setup_keys.py                 # walk through all four keys
    python setup_keys.py --only bing     # redo one: google | bing | opr | moz
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BACKLINKS_CONFIG, GOOGLE_CONFIG, load_json, save_secure_json  # noqa: E402
import check_setup as chk  # noqa: E402


def project_id() -> str:
    sa_path = load_json(GOOGLE_CONFIG).get("service_account_path")
    return load_json(Path(sa_path)).get("project_id", "") if sa_path else ""


def ask_key(label: str) -> str:
    print("  Paste the key and press Enter (nothing shows while you paste; that's normal).")
    print("  Press Enter on an empty line to skip.")
    key = getpass.getpass(f"  {label}: ").strip()
    if key:
        print(f"  Received {len(key)} characters.")
    return key


def choose_after_failure() -> str:
    while True:
        c = input("  [r]etry, [s]ave anyway, or s[k]ip? ").strip().lower()
        if c in ("r", "s", "k"):
            return c


def step(title: str, instructions: list[str], label: str, existing: bool, validate, save) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if existing:
        print("  A key is already saved. Press Enter to keep it, or paste a new one.")
    for line in instructions:
        print("  " + line)
    print()
    while True:
        key = ask_key(label)
        if not key:
            print("  Skipped." if not existing else "  Kept the saved key.")
            return
        ok, msg = validate(key)
        print(("  OK: " if ok else "  Problem: ") + msg)
        if ok:
            save(key)
            print("  Saved.")
            return
        choice = choose_after_failure()
        if choice == "s":
            save(key)
            print("  Saved (not working yet).")
            return
        if choice == "k":
            print("  Skipped.")
            return


# ---------- Google API key (PageSpeed + CrUX) ----------

def validate_google(key: str):
    ok_crux, msg_crux, _ = chk.check_crux(key)
    print("  Testing PageSpeed Insights (takes up to a minute)...")
    ok_psi, msg_psi = chk.check_psi(key)
    msg = f"{msg_crux}; {msg_psi}"
    if not (ok_crux and ok_psi) and ("has not been used" in msg or "disabled" in msg):
        msg += "\n  -> Enable the API (links above), wait 1-2 minutes, then retry."
    return ok_crux and ok_psi, msg


def save_google(key: str):
    cfg = load_json(GOOGLE_CONFIG)
    cfg["api_key"] = key
    save_secure_json(GOOGLE_CONFIG, cfg)


# ---------- Bing Webmaster Tools ----------

def validate_bing(key: str):
    code, sites = chk.bing_sites(key)
    if isinstance(sites, list):
        verified = [s["url"] for s in sites if s["verified"]]
        listing = ", ".join(verified) if verified else "none yet - add your sites in Bing Webmaster Tools"
        return True, f"Bing API works. Verified sites: {listing}"
    return False, f"Bing API error {code}: {sites}"


def save_bing(key: str):
    cfg = load_json(BACKLINKS_CONFIG)
    cfg["bing_api_key"] = key
    _, sites = chk.bing_sites(key)
    if isinstance(sites, list):
        cfg["bing_verified_sites"] = [s["url"] for s in sites if s["verified"]]
    save_secure_json(BACKLINKS_CONFIG, cfg)


# ---------- Open PageRank (free, via Keywords Everywhere) ----------

def validate_opr(key: str):
    r = chk.check_opr(key)
    return r["ok"], r["detail"]


def save_opr(key: str):
    cfg = load_json(BACKLINKS_CONFIG)
    cfg["keywordseverywhere_api_key"] = key
    save_secure_json(BACKLINKS_CONFIG, cfg)


# ---------- Moz (optional) ----------

def validate_moz(key: str):
    return True, "Saved without a live test, to keep your free monthly Moz quota"


def save_moz(key: str):
    cfg = load_json(BACKLINKS_CONFIG)
    cfg["moz_api_key"] = key
    save_secure_json(BACKLINKS_CONFIG, cfg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["google", "bing", "opr", "moz"])
    args = ap.parse_args()

    pid = project_id()
    g, b = load_json(GOOGLE_CONFIG), load_json(BACKLINKS_CONFIG)
    steps = {
        "google": (
            "STEP 1 of 4 - Google API key (required): PageSpeed + Core Web Vitals",
            [
                "Uses your existing Google Cloud project, so it stays free.",
                "1. Enable these two APIs (open each link, click Enable):",
                f"   https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com?project={pid}",
                f"   https://console.cloud.google.com/apis/library/chromeuxreport.googleapis.com?project={pid}",
                "2. Create the key:",
                f"   https://console.cloud.google.com/apis/credentials?project={pid}",
                "   Create credentials > API key > copy it.",
                "3. Recommended: Edit the key > API restrictions > Restrict key >",
                "   tick only 'PageSpeed Insights API' and 'Chrome UX Report API' > Save.",
            ],
            "Google API key", bool(g.get("api_key")), validate_google, save_google,
        ),
        "bing": (
            "STEP 2 of 4 - Bing Webmaster Tools API key (required): keyword volumes + Bing data",
            [
                "1. Open https://www.bing.com/webmasters and sign in (free Microsoft account).",
                "2. Add your sites: 'Import from Google Search Console' adds all of them at once.",
                "   Do the same later for each new client site.",
                "3. Gear icon (Settings, top right) > API access > API Key > Generate > copy.",
            ],
            "Bing API key", bool(b.get("bing_api_key")), validate_bing, save_bing,
        ),
        "opr": (
            "STEP 3 of 4 - Open PageRank key (recommended, free 30,000 domains/month): competitor numbers",
            [
                "1. Open https://openpagerank.keywordseverywhere.com and sign up or sign in",
                "   with a free Keywords Everywhere account. Don't buy credits; they aren't needed.",
                "2. Create the free OPR API key (it starts with opr_live_) and copy it.",
            ],
            "Open PageRank key", bool(b.get("keywordseverywhere_api_key")), validate_opr, save_opr,
        ),
        "moz": (
            "STEP 4 of 4 - Moz API token (optional): Domain Authority for competitor tables",
            [
                "Skip this if you don't want another account. Open PageRank covers most of it.",
                "1. Open https://moz.com/products/api and choose the free plan.",
                "2. In the Moz API dashboard, create/copy your API token.",
            ],
            "Moz API token", bool(b.get("moz_api_key")), validate_moz, save_moz,
        ),
    }
    order = [args.only] if args.only else ["google", "bing", "opr", "moz"]
    print("\nSEO Claude System - free API key setup")
    print("Keys stay on this PC in ~/.config/claude-seo/ and are never shown or sent to the chat.")
    for name in order:
        step(*steps[name])

    print("\n" + "=" * 70)
    print("Done. Back in Claude, say: \"SEO Claude System check setup\".")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nStopped. Anything already saved stays saved.")
