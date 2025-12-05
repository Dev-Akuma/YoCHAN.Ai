#!/usr/bin/env python3
"""
YoChan updater + installer normalizer.

Features:
- If YoChan is a git clone:
    - Check for updates (remote ahead of local).
    - Apply updates via `git pull --ff-only`, but ONLY if working tree is clean.
- If YoChan is NOT a git clone (e.g., downloaded as ZIP):
    - Offer to "convert" this install into a proper git clone:
        - Clone the official repo into a temp directory.
        - Copy user config files (like .env, yochan_apps.user.json) over.
        - Swap directories so your current YoChan folder becomes a git-managed clone.
        - Keep a backup of the old folder.

Note:
- To ensure user config files are never tracked by git, add them to your .gitignore
  in the repo: e.g., .env, yochan_apps.user.json, *.local.json, etc.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple

# ==============================
# === CONFIG ===================
# ==============================

# 🔴 CHANGE THIS to your actual GitHub repo URL
REPO_URL = "https://github.com/Dev-Akuma/YoCHAN.Ai.git"

# Default upstream ref (change to origin/master if you use master)
UPSTREAM_REF = "origin/main"

# Files we consider "user config" that should be preserved on clone/updates.
# These are copied from old non-git installs to the new clone.
USER_CONFIG_FILES = [
    ".env",
    "yochan_apps.user.json",
    # add more here if you create other user-only config files
]


# ==============================
# === BASIC GIT HELPERS =======
# ==============================

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


# ==============================
# === NON-GIT → GIT CLONE =====
# ==============================

def bootstrap_convert_to_git_clone(base_dir: Path) -> tuple[bool, str]:
    """
    Convert a non-git YoChan install into a proper git clone:

    Steps:
    1. Create a backup of the current folder: <name>_backup_<timestamp>.
    2. In the parent folder, `git clone REPO_URL` into <name>_new_clone.
    3. Copy user config files from old folder into new clone.
    4. Move old folder to backup, move new clone to original name.

    Returns:
        (success, message)
    """

    if _is_git_repo(base_dir):
        return False, "This install is already a git clone; no conversion needed."

    parent = base_dir.parent
    name = base_dir.name

    if not REPO_URL or "your-username" in REPO_URL:
        return (
            False,
            "REPO_URL is not configured in yochan_update.py.\n"
            "Please set it to your actual GitHub repository URL.",
        )

    # Paths for new clone + backup
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = parent / f"{name}_backup_{timestamp}"
    clone_dir = parent / f"{name}_new_clone"

    if clone_dir.exists():
        return False, f"Temporary clone directory already exists: {clone_dir}"

    # 1. Clone
    code, out = _run_git(["clone", REPO_URL, str(clone_dir)], cwd=parent)
    if code != 0:
        return False, f"Failed to clone YoChan repo from {REPO_URL}:\n{out}"

    # 2. Copy user config files from old install to new clone
    for rel in USER_CONFIG_FILES:
        src = base_dir / rel
        dst = clone_dir / rel
        if src.exists() and src.is_file():
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            except Exception as e:
                # We don't fail hard on user-file copy; just warn in message.
                print(f"[YoChan updater] Failed to copy user config {src} -> {dst}: {e}")

    # 3. Move old folder aside as backup
    try:
        base_dir.rename(backup_dir)
    except Exception as e:
        # Rollback: remove clone_dir?
        try:
            shutil.rmtree(clone_dir)
        except Exception:
            pass
        return False, f"Failed to move old YoChan folder to backup:\n{e}"

    # 4. Move clone folder into original name
    try:
        clone_dir.rename(base_dir)
    except Exception as e:
        # Try to rollback: move backup back, remove clone_dir
        try:
            backup_dir.rename(base_dir)
        except Exception:
            pass
        try:
            if clone_dir.exists():
                shutil.rmtree(clone_dir)
        except Exception:
            pass
        return False, f"Failed to move new clone into place:\n{e}"

    msg = (
        "YoChan install has been converted into a git-managed clone.\n"
        f"A backup of your previous folder is at:\n{backup_dir}\n\n"
        "Your user config files (like .env, yochan_apps.user.json) were copied over "
        "when possible.\n"
        "You can now use 'Check for updates' for seamless future updates."
    )
    return True, msg


# ==============================
# === UPDATE CHECKING =========
# ==============================

def check_for_updates(repo_dir: Path) -> tuple[bool, bool, str, bool]:
    """
    Return (has_updates, is_dirty, status_message, is_git).

    - has_updates: True if remote is ahead of local (only meaningful if is_git=True).
    - is_dirty:    True if there are uncommitted local changes (only meaningful if is_git=True).
    - status_message: human-readable summary for the UI.
    - is_git:      True if repo_dir is a git repository.
    """
    if not _is_git_repo(repo_dir):
        return (
            False,
            False,
            "This YoChan installation is NOT a git clone.\n"
            "Auto-update is disabled.\n\n"
            "You can convert it into a git-managed install so that future updates "
            "are seamless.",
            False,
        )

    # Check for local modifications (tracked files)
    code, status_out = _run_git(["status", "--porcelain"], repo_dir)
    if code != 0:
        return False, False, f"Failed to read git status:\n{status_out}", True

    is_dirty = bool(status_out.strip())

    # Fetch latest info
    code, fetch_out = _run_git(["fetch", "origin"], repo_dir)
    if code != 0:
        return False, is_dirty, f"Failed to contact remote for updates:\n{fetch_out}", True

    # Compare local HEAD vs upstream
    code, local = _run_git(["rev-parse", "HEAD"], repo_dir)
    if code != 0:
        return False, is_dirty, f"Failed to read local HEAD:\n{local}", True

    code, upstream = _run_git(["rev-parse", UPSTREAM_REF], repo_dir)
    if code != 0:
        return False, is_dirty, (
            f"Failed to read upstream reference {UPSTREAM_REF}:\n{upstream}\n"
            "Make sure your 'origin' is configured and has a 'main' (or master) branch."
        ), True

    if local == upstream:
        if is_dirty:
            return (
                False,
                True,
                "YoChan is up to date, but you have local changes.\n"
                "These won't be overwritten, but you may want to commit/stash them.",
                True,
            )
        return False, False, "YoChan is already up to date.", True

    # Remote is ahead
    if is_dirty:
        return (
            True,
            True,
            "A new version of YoChan is available, but you have local changes.\n\n"
            "Auto-update is disabled while there are local edits.\n"
            "Please commit or stash your changes before updating.",
            True,
        )

    return True, False, "A new version of YoChan is available.", True


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


# ==============================
# === CLI USAGE (OPTIONAL) ====
# ==============================

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    has_updates, is_dirty, msg, is_git = check_for_updates(here)
    print(msg)

    if not is_git:
        ok, convert_msg = bootstrap_convert_to_git_clone(here)
        print(convert_msg)
    elif has_updates and not is_dirty:
        ok, out = apply_updates(here)
        print(out)
