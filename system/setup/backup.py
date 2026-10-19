#!/usr/bin/env python3
"""Back up the SEO Claude System folder: sync the outside Claude files, commit every change, push if a remote is set.

Usage: python system/setup/backup.py ["optional message"]
The GitHub repo must be PRIVATE (client data lives here). Keys never live in this folder.
"""

import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git(*args: str) -> subprocess.CompletedProcess:
    # Uses this folder's git identity (git config user.name / user.email); falls back to a neutral one.
    who = [] if subprocess.run(["git", "-C", str(ROOT), "config", "user.email"], capture_output=True).returncode == 0         else ["-c", "user.name=SEO Claude System", "-c", "user.email=seo-claude-system@localhost"]
    return subprocess.run(["git", "-C", str(ROOT), *who, *args], capture_output=True, text=True)


def main():
    if not (ROOT / ".git").exists():
        sys.exit("backup: this folder is not a git repo yet. Run: git init -b main")
    subprocess.run([sys.executable, str(ROOT / "system" / "setup" / "sync_claude_files.py")], check=False)
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("backup: nothing changed")
    else:
        msg = sys.argv[1] if len(sys.argv) > 1 else f"Backup {dt.date.today().isoformat()}"
        r = git("commit", "-q", "-m", msg)
        print("backup: committed" if r.returncode == 0 else f"backup: commit failed: {r.stderr.strip()}")
    if git("remote").stdout.strip():
        r = git("push", "-q", "origin", "HEAD")
        print("backup: pushed" if r.returncode == 0 else f"backup: push failed: {r.stderr.strip()[-300:]}")
    else:
        print("backup: no remote yet (add the private GitHub repo with: git remote add origin <url>)")


if __name__ == "__main__":
    main()
