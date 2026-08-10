"""Configuration helpers for GitHub user switching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG_PATH = Path.home() / ".github-user-changeable.json"


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the CLI configuration from disk."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {"profiles": {}, "active_profile": None, "repo_policies": {}}

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_config(config: Dict[str, Any], config_path: Optional[Path] = None) -> None:
    """Persist the CLI configuration to disk."""
    path = config_path or DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def get_active_profile(config_path: Optional[Path] = None) -> Optional[str]:
    """Return the name of the active GitHub profile."""
    config = load_config(config_path)
    return config.get("active_profile")


def list_profiles(config_path: Optional[Path] = None) -> list[Dict[str, Any]]:
    """Return the saved profiles with an active flag."""
    config = load_config(config_path)
    active_profile = config.get("active_profile")
    profiles = config.get("profiles", {})
    ordered_profiles: list[Dict[str, Any]] = []
    for profile_name, profile in profiles.items():
        ordered_profiles.append(
            {
                "name": profile_name,
                "github_user": profile.get("github_user"),
                "active": profile_name == active_profile,
            }
        )

    if active_profile:
        ordered_profiles.sort(key=lambda item: (item["name"] != active_profile, item["name"]))
    return ordered_profiles


def list_repo_policies(config_path: Optional[Path] = None) -> list[Dict[str, str]]:
    """Return stored repository policies with path and required profile."""
    config = load_config(config_path)
    policies = config.get("repo_policies", {})
    return [
        {"repo_path": repo_path, "profile_name": profile_name}
        for repo_path, profile_name in sorted(policies.items())
    ]


def add_profile(
    profile_name: str,
    *,
    github_user: str,
    name: str,
    email: str,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create or update a stored GitHub profile."""
    config = load_config(config_path)
    profiles = config.setdefault("profiles", {})
    profiles[profile_name] = {
        "github_user": github_user,
        "name": name,
        "email": email,
    }
    save_config(config, config_path)
    return profiles[profile_name]


def add_repo_policy(repo_path: Path, profile_name: str, config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Associate a repository path with a required profile."""
    config = load_config(config_path)
    normalized_path = str(repo_path.resolve())
    config.setdefault("repo_policies", {})[normalized_path] = profile_name
    save_config(config, config_path)
    return {"repo_path": normalized_path, "profile_name": profile_name}


def ensure_repo_policy(repo_path: Path, config_path: Optional[Path] = None) -> None:
    """Raise an error if the active profile is not allowed to use the given repository."""
    config = load_config(config_path)
    active_profile = config.get("active_profile")
    policies = config.get("repo_policies", {})
    normalized_path = str(repo_path.resolve())

    required_profile = policies.get(normalized_path)
    if required_profile and active_profile != required_profile:
        raise PermissionError(
            f"Repository {repo_path} is restricted to profile '{required_profile}', "
            f"but active profile is '{active_profile}'."
        )
