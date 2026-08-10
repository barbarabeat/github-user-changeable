"""Git and GitHub CLI integration helpers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def apply_profile_to_git(
    profile: Dict[str, Any],
    *,
    git_dir: Optional[Path] = None,
    scope: str = "local",
) -> None:
    """Apply the selected Git profile values to Git configuration."""
    target = Path(git_dir).resolve() if git_dir else Path.cwd()
    if scope not in {"local", "global", "system"}:
        raise ValueError(f"Unsupported Git scope: {scope}")

    if scope == "local":
        result = subprocess.run(
            ("git", "-C", str(target), "rev-parse", "--show-toplevel"),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Could not determine Git repository for '{target}': "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        target = Path(result.stdout.strip()).resolve()

    commands = [
        ("git", "-C", str(target), "config", f"--{scope}", "user.name", profile["name"]),
        ("git", "-C", str(target), "config", f"--{scope}", "user.email", profile["email"]),
        ("git", "-C", str(target), "config", f"--{scope}", "credential.username", profile["github_user"]),
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def sync_github_cli(profile: Dict[str, Any]) -> None:
    """Try to synchronize the current GitHub CLI account with the selected profile."""
    commands = [
        ["gh", "auth", "setup-git"],
        ["gh", "auth", "switch", profile["github_user"]],
    ]
    for command in commands:
        try:
            subprocess.run(command, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            continue
