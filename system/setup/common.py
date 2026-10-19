"""Shared paths and helpers for the SEO Claude System setup scripts.

Standard library only, so these scripts run on any Python 3.10+ without
installing anything. Keys are stored in the same config files the claude-seo
skills already read, so every seo-* skill benefits from the same setup.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOME_DIR = Path(__file__).resolve().parents[2]          # the SEO Claude System folder
CLIENTS_DIR = HOME_DIR / "clients"
TEMPLATES_DIR = HOME_DIR / "system" / "templates"

CONFIG_DIR = Path(os.path.expanduser("~/.config/claude-seo"))
GOOGLE_CONFIG = CONFIG_DIR / "google-api.json"
BACKLINKS_CONFIG = CONFIG_DIR / "backlinks-api.json"

SEO_SCRIPTS = Path(os.path.expanduser("~/.claude/skills/seo/scripts"))
LAUNCHER = SEO_SCRIPTS / "claude-seo"

USER_AGENT = "SEOClaudeSystem/1.0"


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: could not read {path}: {exc}", file=sys.stderr)
        return {}


def save_secure_json(path: Path, data: dict) -> None:
    """Write JSON and restrict the file to the current Windows user."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if os.name == "nt" and os.environ.get("USERNAME"):
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"{os.environ['USERNAME']}:F"],
            capture_output=True, text=True, timeout=10, check=False,
        )


def http_json(url: str, method: str = "GET", body: dict | None = None,
              headers: dict | None = None, timeout: int = 30) -> tuple[int, dict | str]:
    """Return (status, parsed JSON or raw text). Never raises on HTTP errors."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", USER_AGENT)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, raw = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, f"network error: {exc}"
    except UnicodeEncodeError:
        return 0, "request contains non-ASCII characters (a masked or mistyped key?)"
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def google_error(payload) -> str:
    """Short, key-free error text from a Google API error body."""
    if isinstance(payload, dict):
        err = payload.get("error", {})
        if isinstance(err, dict):
            return err.get("message", str(err))[:200]
    return str(payload)[:200]


def git_bash() -> str | None:
    """Git Bash, not WSL's bash.exe, which cannot see the Windows home folder."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if os.path.exists(candidate):
            return candidate
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    return None


def run_seo_script(*args: str, timeout: int = 180) -> tuple[int, dict | str]:
    """Run a bundled claude-seo script through its launcher and parse JSON output."""
    bash = git_bash()
    if not bash or not LAUNCHER.exists():
        return 1, "claude-seo launcher or Git Bash not found"
    proc = subprocess.run(
        [bash, LAUNCHER.as_posix(), "run", *args],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    out = proc.stdout.strip()
    try:
        return proc.returncode, json.loads(out)
    except json.JSONDecodeError:
        return proc.returncode, (out or proc.stderr.strip())[-500:]


def normalize_domain(raw: str) -> str:
    d = raw.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = d.split("/")[0].split("?")[0].split("#")[0]
    if d.startswith("www."):
        d = d[4:]
    return d
