#!/usr/bin/env python3
"""Copy the SEO Claude System files that live outside this folder into system/claude/ so git backs them up.

Copies:
  ~/.claude/skills/seo-claude-system/        -> system/claude/skills/seo-claude-system/
  ~/.claude/scheduled-tasks/<client tasks>/  -> system/claude/scheduled-tasks/<task>/   (SKILL.md only)
Keys are never copied: they live in ~/.config/claude-seo and stay there.

Usage: python system/setup/sync_claude_files.py   (run before each commit; backup.py does it for you)
"""

import shutil
from pathlib import Path

HOME = Path.home()
DEST = Path(__file__).resolve().parents[1] / "claude"
CLIENTS = [p.name for p in (Path(__file__).resolve().parents[2] / "clients").iterdir() if p.is_dir()]


def main():
    skill = HOME / ".claude" / "skills" / "seo-claude-system"
    if skill.exists():
        shutil.copytree(skill, DEST / "skills" / "seo-claude-system", dirs_exist_ok=True)
        print(f"copied skill: {skill}")
    tasks = HOME / ".claude" / "scheduled-tasks"
    prefixes = tuple(c.split(".")[0] for c in CLIENTS)
    for task in sorted(tasks.glob("*")) if tasks.exists() else []:
        src = task / "SKILL.md"
        if task.is_dir() and src.exists() and task.name.startswith(prefixes):
            out = DEST / "scheduled-tasks" / task.name
            out.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / "SKILL.md")
            print(f"copied scheduled task: {task.name}")


if __name__ == "__main__":
    main()
