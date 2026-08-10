import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from github_user_changeable.cli import apply_active_profile_to_current_repo, switch_profile
from github_user_changeable.config import (
    add_profile,
    add_repo_policy,
    ensure_repo_policy,
    list_profiles,
    list_repo_policies,
    load_config,
    remove_repo_policy,
)
from github_user_changeable.git_ops import apply_profile_to_git
from github_user_changeable.ui import prompt_menu

DEFAULT_PROFILES = {
    "personal": {
        "github_user": "alice",
        "name": "Alice",
        "email": "alice@example.com",
    },
    "work": {
        "github_user": "alice-company",
        "name": "Alice Work",
        "email": "alice@company.com",
    },
}


def default_config(active_profile="personal", repo_policies=None) -> dict:
    config = {
        "profiles": copy.deepcopy(DEFAULT_PROFILES),
        "active_profile": active_profile,
    }
    if repo_policies is not None:
        config["repo_policies"] = repo_policies
    return config


def write_config(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_switch_profile_updates_current_profile(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, default_config(active_profile="personal"))

    profile = switch_profile("work", config_path=config_path)

    assert profile["github_user"] == "alice-company"
    assert get_active_profile(config_path) == "work"


def test_repo_policy_blocks_non_allowed_profile(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    repo_root = tmp_path / "company-repo"
    repo_root.mkdir()
    write_config(config_path, default_config(active_profile="personal", repo_policies={str(repo_root): "work"}))

    with pytest.raises(PermissionError):
        ensure_repo_policy(repo_root, config_path=config_path)


def test_add_repo_policy_records_repository(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, default_config(active_profile="personal"))

    repo_path = tmp_path / "company-repo"
    repo_path.mkdir()

    policy = add_repo_policy(repo_path, "work", config_path=config_path)

    assert policy["profile_name"] == "work"
    config = load_config(config_path)
    assert config["repo_policies"][str(repo_path)] == "work"


def test_switch_profile_applies_git_identity(tmp_path: Path) -> None:
    repo_dir = tmp_path / "demo-repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True, text=True)

    config_path = tmp_path / "config.json"
    write_config(config_path, default_config(active_profile="personal"))

    switch_profile("work", config_path=config_path, git_dir=repo_dir, scope="local")

    name = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "user.name"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    email = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "user.email"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert name == "Alice Work"
    assert email == "alice@company.com"


def test_add_profile_persists_new_profile(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    add_profile(
        "work",
        github_user="alice-company",
        name="Alice Work",
        email="alice@company.com",
        config_path=config_path,
    )

    config = load_config(config_path)
    assert config["profiles"]["work"]["github_user"] == "alice-company"


def test_list_profiles_returns_saved_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, default_config(active_profile="work"))

    profiles = list_profiles(config_path=config_path)

    assert profiles[0]["name"] == "work"
    assert profiles[0]["active"] is True
    assert profiles[1]["name"] == "personal"


def test_list_repo_policies_returns_recorded_policies(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    repo_path = tmp_path / "company-repo"
    repo_path.mkdir()
    write_config(config_path, default_config(active_profile="personal", repo_policies={str(repo_path): "work"}))

    policies = list_repo_policies(config_path=config_path)

    assert policies == [{"repo_path": str(repo_path.resolve()), "profile_name": "work"}]


def test_remove_repo_policy_deletes_recorded_policy(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    repo_path = tmp_path / "company-repo"
    repo_path.mkdir()
    write_config(config_path, default_config(active_profile="personal", repo_policies={str(repo_path): "work"}))

    removed = remove_repo_policy(repo_path, config_path=config_path)
    config = load_config(config_path)

    assert removed == {"repo_path": str(repo_path.resolve()), "profile_name": "work"}
    assert str(repo_path.resolve()) not in config["repo_policies"]


def test_remove_repo_policy_returns_none_when_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    repo_path = tmp_path / "company-repo"
    repo_path.mkdir()
    write_config(config_path, default_config(active_profile="personal"))

    removed = remove_repo_policy(repo_path, config_path=config_path)

    assert removed is None


def test_apply_profile_to_git_sets_local_identity(tmp_path: Path) -> None:
    repo_dir = tmp_path / "demo-repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True, text=True)

    profile = DEFAULT_PROFILES["work"]

    apply_profile_to_git(profile, git_dir=repo_dir, scope="local")

    name = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "user.name"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    email = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "user.email"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert name == "Alice Work"
    assert email == "alice@company.com"


def test_apply_active_profile_to_current_repo_uses_active_profile(tmp_path: Path) -> None:
    repo_dir = tmp_path / "demo-repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True, text=True)

    config_path = tmp_path / "config.json"
    write_config(config_path, default_config(active_profile="personal"))

    current = Path.cwd()
    try:
        os.chdir(repo_dir)
        apply_active_profile_to_current_repo(config_path=config_path)
    finally:
        os.chdir(current)

    name = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "user.name"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    email = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "user.email"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert name == "Alice Work"
    assert email == "alice@company.com"


def test_prompt_menu_returns_selected_option(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(["3"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    selected = prompt_menu(["Show profile", "List profiles", "Switch profile"])

    assert selected == "Switch profile"


def test_switch_profile_attempts_github_cli_sync(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, default_config(active_profile=None))

    commands: list[list[str]] = []

    def fake_run(command, capture_output=False, text=False, check=False):
        commands.append(list(command))

        class DummyResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return DummyResult()

    monkeypatch.setattr("github_user_changeable.git_ops.subprocess.run", fake_run)

    switch_profile("work", config_path=config_path)

    assert any(command[:3] == ["gh", "auth", "setup-git"] for command in commands)
    assert any(command[:3] == ["gh", "auth", "switch"] for command in commands)
