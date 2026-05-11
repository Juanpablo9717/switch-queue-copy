"""
Category count chip — small pill showing a category and how many files of
that category exist in a game (e.g. "DLC · 5").

Used inside the collapsed game row so the user can see the contents
without expanding.
"""

from __future__ import annotations

import flet as ft

from .. import theme


def category_count_chip(category: str, count: int) -> ft.Container:
    """Render a tiny rounded chip like 'BASE · 1' or 'DLC · 38'."""
    style = theme.current.tag_styles[category]
    return ft.Container(
        content=ft.Text(
            f"{style['label']} · {count}",
            size=10,
            weight=ft.FontWeight.W_700,
            color=style["fg"],
        ),
        bgcolor=style["bg"],
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )
