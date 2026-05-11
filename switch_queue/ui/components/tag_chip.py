"""
Tag chip — small rounded pill that labels a file as BASE / UPDATE / DLC.

Reads tag styles from the active theme so it adapts to light/dark mode.
"""

from __future__ import annotations

import flet as ft

from .. import theme


def tag_chip(category: str) -> ft.Container:
    """Render a small rounded category tag like Ant Design's <Tag>."""
    style = theme.current.tag_styles[category]
    return ft.Container(
        content=ft.Text(
            style["label"],
            size=10,
            weight=ft.FontWeight.W_700,
            color=style["fg"],
        ),
        bgcolor=style["bg"],
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )
