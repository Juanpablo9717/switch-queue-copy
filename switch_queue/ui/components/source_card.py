"""
Source card — one row in the "Origen" list.

Shows folder icon, name, full path (muted), a count badge, and a remove
button. Theme-aware via `theme.current`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import flet as ft

from ...i18n import t
from .. import theme


def source_card(
    *,
    src: Path,
    game_count: int,
    on_remove: Callable[[Path], None],
    disabled: bool = False,
) -> ft.Container:
    th = theme.current
    label = t("label.juego") if game_count == 1 else t("label.juegos")
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.FOLDER_ROUNDED, color=th.primary, size=18),
                ft.Column(
                    controls=[
                        ft.Text(src.name, size=13, weight=ft.FontWeight.W_500, color=th.text),
                        ft.Text(
                            str(src),
                            size=10,
                            color=th.text_muted,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=1,
                    tight=True,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Text(
                        f"{game_count} {label}",
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=th.primary_fg,
                    ),
                    bgcolor=th.primary_bg,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                    border_radius=10,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE_ROUNDED,
                    tooltip=t("tooltip.remove_source"),
                    icon_size=16,
                    on_click=lambda e, p=src: on_remove(p),
                    disabled=disabled,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        bgcolor=th.surface_2,
        border=ft.Border.all(1, th.border),
        border_radius=8,
    )
