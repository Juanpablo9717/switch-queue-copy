"""
Main view — composes the page from the App's controls.

The App owns all stateful Flet control references (text fields, progress
bars, buttons that flip enabled/disabled, etc.). This module's job is
layout: it takes those refs and arranges them into the final page.

Reads colors from `theme.current` so it adapts to light/dark mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ...i18n import t
from .. import theme

if TYPE_CHECKING:
    from ...app import App


def section_header(label: str) -> ft.Control:
    th = theme.current
    return ft.Text(label.upper(), size=11, weight=ft.FontWeight.W_700, color=th.text_muted)


def card(*children: ft.Control, expand: bool | int | None = None) -> ft.Container:
    th = theme.current
    return ft.Container(
        content=ft.Column(controls=list(children), spacing=10, expand=expand),
        padding=ft.Padding.all(16),
        bgcolor=th.surface,
        border=ft.Border.all(1, th.border),
        border_radius=12,
        expand=expand,
    )


def appbar(*, trailing: list[ft.Control] | None = None) -> ft.Container:
    """Top bar: brand on the left, optional trailing controls on the right."""
    th = theme.current
    children: list[ft.Control] = [
        ft.Icon(ft.Icons.VIDEOGAME_ASSET_ROUNDED, color=th.primary, size=22),
        ft.Text(t("app.title"), size=16, weight=ft.FontWeight.W_600, color=th.text),
        ft.Container(expand=True),
    ]
    if trailing:
        children.extend(trailing)

    return ft.Container(
        content=ft.Row(
            controls=children,
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=24, vertical=10),
        bgcolor=th.surface,
        border=ft.Border.only(bottom=ft.BorderSide(1, th.border)),
    )


def build_main_view(app: "App") -> ft.Column:
    """Assemble the full page from the App's owned controls."""
    th = theme.current

    sources_card = card(
        section_header(t("section.source")),
        ft.Container(content=app.sources_list, padding=ft.Padding.only(top=6, bottom=4)),
        app.sources_empty,
        ft.Row(
            controls=[app.btn_add_folder, app.btn_add_many, app.btn_clear_sources],
            spacing=8,
        ),
    )

    dest_card = card(
        section_header(t("section.dest")),
        ft.Row(
            controls=[app.dest_field, app.btn_pick_dest, app.btn_pick_mtp],
            spacing=8,
        ),
        app.cb_overwrite,
    )

    queue_card = card(
        ft.Row(controls=[section_header(t("section.queue")), ft.Container(expand=True)]),
        ft.Row(
            controls=[
                app.queue_summary,
                ft.Container(expand=True),
                app.btn_expand_all,
                app.btn_collapse_all,
                ft.VerticalDivider(width=12, color=th.border),
                app.btn_mark_all,
                app.btn_unmark_all,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Container(
            content=ft.Column(
                controls=[app.queue_list, app.queue_empty],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        ),
        expand=True,
    )

    bottom = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(controls=[app.status_text, ft.Container(expand=True), app.speed_text]),
                ft.Row(
                    controls=[
                        ft.Text(t("label.archivo"), size=10, color=th.text_muted, width=60),
                        ft.Container(content=app.file_pb, expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Text(t("label.cola"), size=10, color=th.text_muted, width=60),
                        ft.Container(content=app.global_pb, expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[app.btn_start, app.btn_pause, app.btn_skip, app.btn_cancel],
                    spacing=8,
                ),
            ],
            spacing=8,
        ),
        padding=ft.Padding.symmetric(horizontal=24, vertical=14),
        bgcolor=th.surface,
        border=ft.Border.only(top=ft.BorderSide(1, th.border)),
    )

    scrollable = ft.Container(
        content=ft.Column(
            controls=[sources_card, dest_card, queue_card],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=ft.Padding.symmetric(horizontal=24, vertical=16),
        expand=True,
    )

    return ft.Column(
        controls=[
            appbar(trailing=[app.btn_toggle_logs, app.btn_settings]),
            scrollable,
            bottom,
            app.log_panel_holder,
        ],
        spacing=0,
        expand=True,
    )
