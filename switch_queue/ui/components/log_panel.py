"""
In-app log drawer (VS Code / Postman style).

Pure builder: takes a list of LogEntry plus callbacks for the action
buttons, returns the panel control. The App keeps the entry list and
calls a refresh whenever new lines arrive.

Visual:
    [12:34:56]  INFO   Queue started: 47 files · 32.4 GB
    [12:34:57]  INFO   Copying: file1.nsp
    [12:34:59]  OK     file1.nsp ✓
    [12:35:02]  WARN   Skipped (existing): file2.nsp
    [12:35:05]  ERROR  Upload failed: device disconnected

Monospace font, hairline lines, level color-coded so errors pop
without being noisy.
"""

from __future__ import annotations

from typing import Callable, Iterable

import flet as ft

from ...core import LOG_DEBUG, LOG_ERROR, LOG_INFO, LOG_WARN, LogEntry
from ...i18n import t
from .. import theme

# Fixed-width fonts that ship with Windows / common installs.
LOG_FONT = "Consolas, 'Cascadia Mono', 'Courier New', monospace"


def _level_color(level: str) -> str:
    """Pick a foreground color for the level token in the current theme."""
    th = theme.current
    if level == LOG_ERROR:
        return th.danger
    if level == LOG_WARN:
        # Reuse the UPDATE tag color — it's the established "warn" tone.
        return th.tag_styles["update"]["fg"]
    if level == LOG_DEBUG:
        return th.text_muted
    return th.primary  # info


def _level_label(level: str) -> str:
    """Right-padded fixed-width label so columns line up."""
    return level.upper().ljust(5)


def _format_line(entry: LogEntry) -> tuple[str, str, str, str]:
    """Return (timestamp, level_text, level_color, message)."""
    ts = entry.timestamp.strftime("%H:%M:%S")
    return ts, _level_label(entry.level), _level_color(entry.level), entry.message


def build_log_panel(
    *,
    entries: Iterable[LogEntry],
    on_clear: Callable,
    on_copy: Callable,
    on_close: Callable,
    visible: bool,
) -> ft.Container:
    """Bottom drawer with the log list + clear/copy/close actions."""
    th = theme.current

    # ----- Lines -----
    line_views: list[ft.Control] = []
    for entry in entries:
        ts, level_text, level_color, msg = _format_line(entry)
        line_views.append(
            ft.Row(
                controls=[
                    ft.Text(ts, size=11, color=th.text_muted, font_family=LOG_FONT),
                    ft.Text(
                        level_text,
                        size=11,
                        color=level_color,
                        weight=ft.FontWeight.W_700,
                        font_family=LOG_FONT,
                    ),
                    ft.Text(
                        msg,
                        size=11,
                        color=th.text,
                        font_family=LOG_FONT,
                        selectable=True,
                        expand=True,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    if not line_views:
        line_views.append(
            ft.Container(
                content=ft.Text(
                    t("logs.empty"),
                    size=11,
                    italic=True,
                    color=th.text_muted,
                    font_family=LOG_FONT,
                ),
                padding=ft.Padding.all(8),
            )
        )

    log_view = ft.Column(
        controls=line_views,
        spacing=2,
        scroll=ft.ScrollMode.AUTO,
        auto_scroll=True,  # always pin to the latest line
    )

    # ----- Header (title + actions) -----
    header = ft.Row(
        controls=[
            ft.Icon(ft.Icons.TERMINAL_ROUNDED, size=14, color=th.text_muted),
            ft.Text(
                t("logs.title"),
                size=11,
                weight=ft.FontWeight.W_700,
                color=th.text_muted,
            ),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.CONTENT_COPY_ROUNDED,
                tooltip=t("logs.copy"),
                icon_size=15,
                on_click=lambda e: on_copy(),
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                tooltip=t("logs.clear"),
                icon_size=15,
                on_click=lambda e: on_clear(),
            ),
            ft.IconButton(
                icon=ft.Icons.CLOSE_ROUNDED,
                tooltip=t("logs.close"),
                icon_size=15,
                on_click=lambda e: on_close(),
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                header,
                ft.Container(
                    content=log_view,
                    bgcolor=th.bg,
                    border=ft.Border.all(1, th.border),
                    border_radius=6,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                    expand=True,
                ),
            ],
            spacing=6,
            expand=True,
        ),
        padding=ft.Padding.symmetric(horizontal=24, vertical=10),
        bgcolor=th.surface,
        border=ft.Border.only(top=ft.BorderSide(1, th.border)),
        height=220,
        visible=visible,
    )
