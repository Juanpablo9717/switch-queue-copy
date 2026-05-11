"""
Game row — one ExpansionTile per game.

The collapsed header shows at-a-glance info so the user doesn't need to
expand every game to know what's inside:
    [☑] Game name  [BASE·1] [UPDATE·1] [DLC·5]   7/10 · 3.38 GB   ↑ ↓ 🗑  ▾

The expanded body lists each file with its checkbox, tag, name and size.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from ...core import Game, GameFile
from ...i18n import t
from ...utils import fmt_size
from .. import theme
from .category_count_chip import category_count_chip
from .tag_chip import tag_chip


def game_row(
    *,
    game: Game,
    idx: int,
    total: int,
    ordered_files: list[GameFile],
    on_toggle_game: Callable[[Game], None],
    on_toggle_file: Callable[[Game, GameFile], None],
    on_move: Callable[[Game, int], None],
    on_remove: Callable[[Game], None],
    on_expand_change: Callable[[Game, bool], None],
    is_copying: bool,
    expanded: bool = False,
) -> ft.Control:
    th = theme.current
    is_first = idx == 0
    is_last = idx == total - 1

    # ---- Collapsed-header summary ----
    counts: dict[str, int] = {"base": 0, "update": 0, "dlc": 0}
    for f in game.files:
        counts[f.category] = counts.get(f.category, 0) + 1
    count_chips: list[ft.Control] = [
        category_count_chip(cat, n) for cat, n in counts.items() if n > 0
    ]

    sel_count = sum(1 for f in game.files if f.selected)
    total_count = len(game.files)
    selected_size = sum(f.size for f in game.files if f.selected)

    # "7/10 · 3.38 GB"  — concise meta on the right of the header
    summary_text = ft.Text(
        f"{sel_count}/{total_count} · {fmt_size(selected_size)}",
        size=12,
        weight=ft.FontWeight.W_500,
        color=th.text_muted,
    )

    # ---- Title row ----
    title = ft.Row(
        controls=[
            ft.Checkbox(
                value=game.selected,
                on_change=lambda e, g=game: on_toggle_game(g),
                disabled=is_copying,
            ),
            ft.Text(
                game.name,
                size=13,
                weight=ft.FontWeight.W_600,
                color=th.text,
                expand=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Row(controls=count_chips, spacing=6, tight=True),
            summary_text,
            ft.IconButton(
                icon=ft.Icons.ARROW_UPWARD_ROUNDED,
                icon_size=16,
                tooltip=t("tooltip.move_up"),
                disabled=is_copying or is_first,
                on_click=lambda e, g=game: on_move(g, -1),
            ),
            ft.IconButton(
                icon=ft.Icons.ARROW_DOWNWARD_ROUNDED,
                icon_size=16,
                tooltip=t("tooltip.move_down"),
                disabled=is_copying or is_last,
                on_click=lambda e, g=game: on_move(g, 1),
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                icon_size=16,
                tooltip=t("tooltip.remove_game"),
                icon_color=th.danger,
                disabled=is_copying,
                on_click=lambda e, g=game: on_remove(g),
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ---- Expanded body: one row per file ----
    file_rows: list[ft.Control] = []
    for gf in ordered_files:
        file_rows.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Checkbox(
                            value=gf.selected,
                            on_change=lambda e, g=game, f=gf: on_toggle_file(g, f),
                            disabled=is_copying,
                        ),
                        tag_chip(gf.category),
                        ft.Text(
                            str(gf.rel),
                            size=12,
                            color=th.text,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(fmt_size(gf.size), size=11, color=th.text_muted),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=14, vertical=4),
            )
        )

    return ft.Container(
        content=ft.ExpansionTile(
            title=title,
            controls=file_rows,
            tile_padding=ft.Padding.symmetric(horizontal=10, vertical=0),
            controls_padding=ft.Padding.only(left=8, right=8, bottom=8),
            collapsed_bgcolor=th.surface,
            bgcolor=th.surface,
            text_color=th.text,
            collapsed_text_color=th.text,
            icon_color=th.text_muted,
            collapsed_icon_color=th.text_muted,
            expanded=expanded,
            show_trailing_icon=True,
            min_tile_height=44,
            on_change=lambda e, g=game: on_expand_change(g, bool(e.control.expanded)),
        ),
        bgcolor=th.surface,
        border=ft.Border.all(1, th.border),
        border_radius=8,
    )
