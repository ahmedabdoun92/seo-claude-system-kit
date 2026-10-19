#!/usr/bin/env python3
"""Install the SEO Claude System for Claude Code on this computer.

What it does:
  1. Checks Python 3.10+, git and (on Windows) Git Bash.
  2. Checks that the free claude-seo skills are installed (the system uses their Google, PageSpeed and Moz tools).
  3. Installs the `seo-claude-system` skill into ~/.claude/skills/ with this folder's path filled in,
     so you can say "SEO Claude System" in Claude Code from any folder.
  4. Creates the clients/ folder.
Nothing is downloaded and no keys are asked for here. Keys are added later with system/setup/setup_keys.py.

Usage:
    python install.py            # install / update
    python install.py --check    # only report what is missing
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL_TEMPLATE = ROOT / "system" / "skill" / "SKILL.md"
SKILL_DEST = Path.home() / ".claude" / "skills" / "seo-claude-system" / "SKILL.md"
CLAUDE_SEO = Path.home() / ".claude" / "skills" / "seo" / "scripts" / "claude-seo"
CLAUDE_SEO_REPO = "https://github.com/AgriciDaniel/claude-seo"


def line(ok: bool, what: str, fix: str = ""):
    print(f"  [{'ok' if ok else '!!'}] {what}" + (f"\n       -> {fix}" if fix and not ok else ""))
    return ok


def git_bash_found() -> bool:
    if os.name != "nt":
        return shutil.which("bash") is not None
    return any(Path(p).exists() for p in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report, change nothing")
    a = ap.parse_args()

    print("SEO Claude System: install check\n")
    ok = True
    ok &= line(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (3.10+ needed)", "Install Python 3.10 or newer from python.org")
    ok &= line(shutil.which("git") is not None, "git", "Install Git from git-scm.com")
    ok &= line(git_bash_found(), "bash (Git Bash on Windows)", "Install Git for Windows; it includes Git Bash")
    seo_ok = line(CLAUDE_SEO.exists(), "claude-seo skills (free, MIT)",
                  f"Install them first: follow the steps at {CLAUDE_SEO_REPO}, then run this installer again")
    ok &= seo_ok

    if a.check:
        print("\nCheck only: nothing changed.")
        return

    text = SKILL_TEMPLATE.read_text(encoding="utf-8").replace("{{HOME_SCS}}", ROOT.as_posix())
    SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
    existed = SKILL_DEST.exists()
    SKILL_DEST.write_text(text, encoding="utf-8")
    line(True, f"skill {'updated' if existed else 'installed'}: {SKILL_DEST}")
    (ROOT / "clients").mkdir(exist_ok=True)
    line(True, f"clients folder: {ROOT / 'clients'}")

    print("\nNext steps:")
    if not seo_ok:
        print(f"  1. Install claude-seo ({CLAUDE_SEO_REPO}) and run: python install.py")
    print("  - Free Google access (Search Console, GA4, PageSpeed): in Claude Code, run /seo google setup")
    print(f"  - Save optional free keys (Bing, Open PageRank, Moz): python \"{(ROOT / 'system' / 'setup' / 'setup_keys.py').as_posix()}\"")
    print("  - Open Claude Code and say: SEO Claude System   (it checks your setup, then onboards your first client)")
    if not ok:
        print("\nSome checks failed (marked !!). Fix them, then run this again.")


if __name__ == "__main__":
    main()
