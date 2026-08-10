"""Command-line interface for switching GitHub identities safely."""

from __future__ import annotations

import argparse
from pathlib import Path

from github_user_changeable.config import (
    add_profile,
    add_repo_policy,
    ensure_repo_policy,
    get_active_profile,
    list_profiles,
    list_repo_policies,
    load_config,
)
from github_user_changeable.git_ops import apply_profile_to_git, sync_github_cli
from github_user_changeable.ui import prompt_menu


def switch_profile(
    profile_name: str,
    *,
    config_path: Path | None = None,
    git_dir: Path | None = None,
    scope: str = "local",
) -> dict:
    """Switch the active GitHub profile and update Git identity."""
    from github_user_changeable.config import load_config, save_config

    config = load_config(config_path)
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        raise KeyError(f"Unknown profile: {profile_name}")

    config["active_profile"] = profile_name
    save_config(config, config_path)

    profile = profiles[profile_name]
    apply_profile_to_git(profile, git_dir=git_dir, scope=scope)
    sync_github_cli(profile)
    return profile


def apply_active_profile_to_current_repo(*, config_path: Path | None = None) -> None:
    config = load_config(config_path)
    profile_name = config.get("active_profile")
    if not profile_name:
        return

    try:
        ensure_repo_policy(Path.cwd(), config_path=config_path)
    except PermissionError as exc:
        raise SystemExit(
            f"Active profile '{profile_name}' is blocked by repository policy: {exc}"
        )


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(description="Manage GitHub profiles safely")
    parser.add_argument("--switch", dest="switch_profile_name", help="Switch to a saved profile")
    parser.add_argument("--list-profiles", action="store_true", help="List the saved profiles")
    parser.add_argument("--add-profile", dest="add_profile_name", help="Create a new GitHub profile")
    parser.add_argument("--github-user", dest="github_user", help="GitHub username for the new profile")
    parser.add_argument("--name", dest="profile_name_value", help="Display name for the new profile")
    parser.add_argument("--email", dest="profile_email", help="Email for the new profile")
    parser.add_argument("--add-policy", dest="repo_policy_path", help="Protect a repository with a required profile")
    parser.add_argument("--policy-profile", dest="policy_profile_name", help="Profile required by the repository policy")
    parser.add_argument("--list-policies", action="store_true", help="List saved repository policies")
    parser.add_argument("--config", dest="config_path", help="Path to the config file")
    parser.add_argument("--scope", choices=["local", "global", "system"], default="local", help="Git scope for the identity update")
    parser.add_argument("--git-dir", dest="git_dir", help="Path to the repository where Git identity should be updated")
    return parser


def main() -> int:
    """Run the CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config_path).expanduser() if args.config_path else None

    if args.list_profiles:
        profiles = list_profiles(config_path=config_path)
        for profile in profiles:
            marker = "*" if profile["active"] else "-"
            print(f"{marker} {profile['name']} ({profile['github_user']})")
        return 0

    if args.list_policies:
        policies = list_repo_policies(config_path=config_path)
        if not policies:
            print("No repository policies configured.")
            return 0
        for policy in policies:
            print(f"{policy['repo_path']} -> {policy['profile_name']}")
        return 0

    if args.add_profile_name:
        if not all([args.github_user, args.profile_name_value, args.profile_email]):
            raise SystemExit("--github-user, --name and --email are required when creating a profile")
        add_profile(
            args.add_profile_name,
            github_user=args.github_user,
            name=args.profile_name_value,
            email=args.profile_email,
            config_path=config_path,
        )
        print(f"Added profile '{args.add_profile_name}'.")
        return 0

    if args.switch_profile_name:
        switch_profile(
            args.switch_profile_name,
            config_path=config_path,
            git_dir=Path(args.git_dir).expanduser() if args.git_dir else None,
            scope=args.scope,
        )
        print(f"Switched to profile '{args.switch_profile_name}'.")
        return 0

    if args.repo_policy_path and args.policy_profile_name:
        add_repo_policy(Path(args.repo_policy_path).expanduser(), args.policy_profile_name, config_path=config_path)
        print(f"Added policy for {args.repo_policy_path} -> {args.policy_profile_name}.")
        return 0

    if not any([args.switch_profile_name, args.list_profiles, args.add_profile_name, args.repo_policy_path, args.list_policies]):
        apply_active_profile_to_current_repo(config_path=config_path)
        options = ["Show current profile", "List profiles", "Switch profile", "Add profile", "Add repo policy", "List repo policies"]
        selection = prompt_menu(options)

        if selection == "Show current profile":
            active = get_active_profile(config_path)
            print(f"Active profile: {active or 'none'}")
            return 0

        if selection == "List profiles":
            profiles = list_profiles(config_path=config_path)
            for profile in profiles:
                marker = "*" if profile["active"] else "-"
                print(f"{marker} {profile['name']} ({profile['github_user']})")
            return 0

        if selection == "Switch profile":
            profiles = list_profiles(config_path=config_path)
            if not profiles:
                print("No profiles configured yet.")
                return 0
            selected_name = prompt_menu([profile["name"] for profile in profiles])
            switch_profile(selected_name, config_path=config_path)
            print(f"Switched to profile '{selected_name}'.")
            return 0

        if selection == "Add profile":
            profile_name = input("Profile name: ").strip()
            github_user = input("GitHub username: ").strip()
            display_name = input("Display name: ").strip()
            email = input("Email: ").strip()
            add_profile(profile_name, github_user=github_user, name=display_name, email=email, config_path=config_path)
            print(f"Added profile '{profile_name}'.")
            return 0

        if selection == "Add repo policy":
            repo_path = input("Repository path: ").strip()
            profile_name = input("Required profile: ").strip()
            add_repo_policy(Path(repo_path).expanduser(), profile_name, config_path=config_path)
            print(f"Added policy for {repo_path} -> {profile_name}.")
            return 0

        if selection == "List repo policies":
            policies = list_repo_policies(config_path=config_path)
            if not policies:
                print("No repository policies configured.")
                return 0
            for policy in policies:
                print(f"{policy['repo_path']} -> {policy['profile_name']}")
            return 0

    active = get_active_profile(config_path)
    print(f"Active profile: {active or 'none'}")
    return 0
