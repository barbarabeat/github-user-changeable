# 😊 GitHub User Switcher

This project provides a small installable CLI to switch between GitHub identities safely on the same machine.

The command-line interface is organized into focused modules for configuration, Git/GitHub integration, and the interactive terminal UI.

## Features

- Store multiple GitHub profiles in a JSON configuration file.
- Show the currently active profile and the available ones.
- Switch profiles with a simple command.
- Protect specific repositories so they can only be used with the right profile.

## Installation

```bash
pip install -e .
```

## Usage

Run the interactive menu:

```bash
git-my-user
```

The menu lists the available actions and lets you choose them with a numbered option. It now uses a more visual terminal panel with headers and boxed sections, similar to a lightweight application interface.

Show the currently active profile:

```bash
git-my-user
```

List all saved profiles:

```bash
git-my-user --list-profiles
```

Create a profile:

```bash
git-my-user --add-profile work --github-user alice-company --name "Alice Work" --email alice@company.com
```

Switch to a profile and update the Git identity for the current repository:

```bash
git-my-user --switch work
```

To protect a repository:

```bash
git-my-user --add-policy /path/to/repo work
```

If you want Git to expose it as a Git alias:

```bash
git config --global alias.my-user '!git-my-user'
```

Then you can run:

```bash
git my-user
```
