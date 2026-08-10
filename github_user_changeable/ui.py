"""Interactive UI helpers for the GitHub user switcher."""

from __future__ import annotations

from typing import List


class Style:
    """Simple ANSI styling helpers for terminal output."""

    HEADER = "\033[96m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def render_header(title: str) -> None:
    """Render an application header."""
    print(f"{Style.HEADER}{Style.BOLD}=== {title} ==={Style.ENDC}")


def render_box(lines: List[str]) -> None:
    """Render a simple boxed panel in the terminal."""
    width = max(len(line) for line in lines) + 4
    print(f"{Style.OKCYAN}┌{'─' * width}┐{Style.ENDC}")
    for line in lines:
        print(f"{Style.OKCYAN}│ {line.ljust(width - 2)} │{Style.ENDC}")
    print(f"{Style.OKCYAN}└{'─' * width}┘{Style.ENDC}")


def prompt_menu(options: list[str]) -> str:
    """Render a simple interactive menu and return the selected option."""
    render_header("GitHub User Switcher")
    render_box(["Choose an action:"] + [f"{index}. {option}" for index, option in enumerate(options, start=1)])

    while True:
        try:
            choice = input(f"{Style.BOLD}Select an option: {Style.ENDC}").strip()
            index = int(choice) - 1
            if 0 <= index < len(options):
                return options[index]
        except ValueError:
            pass
        print(f"{Style.WARNING}Please select a valid option.{Style.ENDC}")
