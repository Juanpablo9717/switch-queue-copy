"""
Entry point: `python -m switch_queue` or via the installed `switch-queue-copy`
console/GUI script (defined in pyproject.toml).
"""

from __future__ import annotations

import flet as ft

from .app import App


def main() -> None:
    """Launch the Flet desktop window."""
    ft.run(_target)


def _target(page: ft.Page) -> None:
    App(page)


if __name__ == "__main__":
    main()
