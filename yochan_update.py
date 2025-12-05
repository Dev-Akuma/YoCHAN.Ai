#!/usr/bin/env python3
"""
Simple git-based updater for YoChan.

- Only works if YoChan is installed as a git clone.
- NEVER overwrites local modifications: if the working tree is dirty,
  it will refuse to auto-update and tell you to commit/stash first.

We assume:
- Your main branch is 'main'. If you use 'master', adjust UPSTREAM_REF.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple

# Change this if your default branch is different
UPSTREAM_REF = "origin/main"


def _run_git(args, cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
        )
        out = result.stdout.strip() or result.stderr.strip()
        return result.returncode, out
    except Exception as e:
        return 1, str(e)


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").is_dir()


def check_for_updates(repo_dir: Path) -> tuple[bool, bool, str]:
    """
    Return (has_updates, is_dirty, status_message).

    - has_updates: True if remote is ahead of local.
    - is_dirty:    True if there are uncommitted local changes.
    - status_message: human-readable summary for the UI.
    """
    if not _is_git_repo(repo_dir):
        return (
            False,
            False,
            "This YoChan installation is not a git clone (.git folder missing). "
            "Auto-update via configurator is disabled.",
        )

    # Check for local modifications (tracked + untracked)
    code, status_out = _run_git(["status", "--porcelain"], repo_dir)
    if code != 0:
        return False, False, f"Failed to read git status:\n{status_out}"

    is_dirty = bool(status_out.strip())

    # Fetch latest refs
    code, fetch_out = _run_git(["fetch", "origin"], repo_dir)
    if code != 0:
        return False, is_dirty, f"Failed to contact remote for updates:\n{fetch_out}"

    # Compare local HEAD vs upstream
    code, local = _run_git(["rev-parse", "HEAD"], repo_dir)
    if code != 0:
        return False, is_dirty, f"Failed to read local HEAD:\n{local}"

    code, upstream = _run_git(["rev-parse", UPSTREAM_REF], repo_dir)
    if code != 0:
        return False, is_dirty, (
            f"Failed to read upstream reference {UPSTREAM_REF}:\n{upstream}\n"
            "Make sure your 'origin' is configured and has a 'main' branch."
        )

    if local == upstream:
        # Up to date
        if is_dirty:
            return (
                False,
                True,
                "YoChan is up to date, but you have local changes.\n"
                "These won't be overwritten, but you may want to commit/stash them.",
            )
        return False, False, "YoChan is already up to date."

    # Remote is ahead
    if is_dirty:
        return (
            True,
            True,
            "A new version of YoChan is available, but you have local changes.\n\n"
            "Auto-update is disabled while there are local edits.\n"
            "Please commit or stash your changes before updating.",
        )

    return True, False, "A new version of YoChan is available."


def apply_updates(repo_dir: Path) -> tuple[bool, str]:
    """
    Apply updates from remote using `git pull --ff-only`.

    Returns (success, message).
    """
    if not _is_git_repo(repo_dir):
        return False, "Cannot update: this directory is not a git clone."

    code, out = _run_git(["pull", "--ff-only"], repo_dir)
    if code != 0:
        return False, f"git pull failed:\n{out}"

    return True, "YoChan has been updated to the latest version.\nPlease restart the listener."
    

if __name__ == "__main__":
    # Optional CLI usage: python3 yochan_update.py
    here = Path(__file__).resolve().parent
    has_updates, is_dirty, msg = check_for_updates(here)
    print(msg)
    if has_updates and not is_dirty:
        ok, out = apply_updates(here)
        print(out)
