"""
Category chips — the row of BASE / UPDATE / DLC chips that defines copy
priority. Click to select (click again to deselect); the App uses the
current selection to drive the left/right reorder buttons.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from .. import theme


def category_chips(
    *,
    order: list[str],
    selected: str | None,
    on_select: Callable[[str], None],
) -> ft.Row:
    chips: list[ft.Control] = []
    for c in order:
        style = theme.current.tag_styles[c]
        is_sel = c == selected
        chips.append(
            ft.Container(
                content=ft.Text(
                    style["label"],
                    size=11,
                    weight=ft.FontWeight.W_700,
                    color=style["fg"],
                ),
                bgcolor=style["bg"],
                padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                border_radius=12,
                # Highlight only the selected chip; reserve the same 2px
                # border on others (transparent) so layout doesn't shift.
                border=ft.Border.all(2, style["fg"] if is_sel else "transparent"),
                on_click=lambda e, cat=c: on_select(cat),
                ink=True,
            )
        )
    return ft.Row(controls=chips, spacing=8)
