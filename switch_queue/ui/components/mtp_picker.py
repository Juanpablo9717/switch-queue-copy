"""
Flet-native MTP folder picker.

Opens a modal dialog that lists connected MTP devices, lets the user
drill down storage → folder → folder, and confirms a destination via
``mtp://<device>/<storage>/<sub>/<path>`` URI.

Why not Heribert17's bundled tkinter dialog: mixing a tk window with a
Flet/Flutter window in the same process is fragile and looks foreign.
Building it in Flet gives us a consistent dark/light theme and Material
icons.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from ...core.backends.mtp_provider import (
    MtpUnavailable,
    build_destination,
    list_device_folders,
    list_devices,
)
from ...i18n import t
from .. import theme


# ---------------------------------------------------------------------------


class MtpPicker:
    """Modal picker for an MTP destination folder.

    Lifecycle:
        picker = MtpPicker(page, on_select=...)
        picker.show()                           # opens the dialog
        # user navigates and clicks "Elegir aquí" → on_select(uri) fires
    """

    def __init__(
        self,
        page: ft.Page,
        on_select: Callable[[str], None],
    ) -> None:
        self.page = page
        self.on_select = on_select

        # Navigation state
        self._device = None              # PortableDevice | None
        self._path: list[str] = []       # ['Storage', 'sub', ...]

        # Build UI shell
        self._list_view = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=320)
        self._breadcrumb = ft.Text("", size=12, color=theme.current.text_muted)
        self._error_text = ft.Text("", size=11, color=theme.current.danger)
        self._select_btn = ft.FilledButton(
            content=t("btn.choose_here"),
            icon=ft.Icons.CHECK_ROUNDED,
            on_click=self._on_confirm,
            disabled=True,
        )
        self._refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            tooltip=t("tooltip.refresh"),
            on_click=lambda e: self._render_devices(),
            icon_size=18,
        )
        self._dialog = self._build_dialog()

    # -- public ------------------------------------------------------------

    def show(self) -> None:
        self._render_devices()
        self.page.show_dialog(self._dialog)

    # -- ui shell ----------------------------------------------------------

    def _build_dialog(self) -> ft.AlertDialog:
        th = theme.current
        body = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[self._breadcrumb, ft.Container(expand=True), self._refresh_btn],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        content=self._list_view,
                        bgcolor=th.surface_2,
                        border=ft.Border.all(1, th.border),
                        border_radius=8,
                        padding=ft.Padding.all(4),
                    ),
                    self._error_text,
                ],
                spacing=10,
                tight=True,
            ),
            width=540,
        )
        return ft.AlertDialog(
            modal=True,
            bgcolor=th.surface,
            title=ft.Text(
                t("picker.mtp_title"),
                size=16,
                weight=ft.FontWeight.W_600,
                color=th.text,
            ),
            content=body,
            actions=[
                ft.TextButton(t("btn.cancel"), on_click=self._on_cancel),
                self._select_btn,
            ],
        )

    # -- rendering ---------------------------------------------------------

    def _render_devices(self) -> None:
        """Top level: list connected MTP devices."""
        self._device = None
        self._path = []
        self._error_text.value = ""
        self._select_btn.disabled = True
        self._breadcrumb.value = t("picker.mtp_breadcrumb_root")
        self._list_view.controls.clear()

        try:
            devices = list_devices()
        except MtpUnavailable:
            self._error_text.value = t("picker.mtp_install_hint")
            self.page.update()
            return
        except Exception as exc:
            self._error_text.value = t("picker.mtp_enum_error", error=str(exc))
            self.page.update()
            return

        if not devices:
            self._error_text.value = t("picker.mtp_no_devices")
            self.page.update()
            return

        for dev in devices:
            self._list_view.controls.append(self._row(
                icon=ft.Icons.PHONELINK_ROUNDED,
                label=dev.name or dev.devicename,
                sublabel=dev.devicename,
                on_click=lambda e, d=dev: self._open_device(d),
            ))
        self.page.update()

    def _open_device(self, device) -> None:
        self._device = device
        self._path = []
        self._render_current()

    def _render_current(self) -> None:
        """Lists children at the current `_path` of the selected device."""
        self._error_text.value = ""
        self._list_view.controls.clear()

        # Breadcrumb
        crumb_parts = [self._device.name or self._device.devicename, *self._path]
        self._breadcrumb.value = " / ".join(crumb_parts)

        # "Elegir aquí" only enabled once we're inside a folder (>= storage).
        self._select_btn.disabled = len(self._path) < 1

        # Up row (if not at storage list level)
        if self._path:
            self._list_view.controls.append(self._row(
                icon=ft.Icons.ARROW_UPWARD_ROUNDED,
                label=t("picker.mtp_go_up"),
                sublabel=None,
                on_click=lambda e: self._go_up(),
                muted=True,
            ))

        # Children at current path
        try:
            children = list(list_device_folders(self._device, self._path))
        except Exception as exc:
            self._error_text.value = t("picker.mtp_enum_error", error=str(exc))
            self.page.update()
            return

        # Filter to directories/storages only — we don't want to land on a file
        dirs = [c for c in children if getattr(c, "content_type", -1) in (0, 1)]
        # 0 = STORAGE, 1 = DIRECTORY (per Heribert17)

        for child in dirs:
            self._list_view.controls.append(self._row(
                icon=ft.Icons.FOLDER_ROUNDED,
                label=child.name or child._plain_name,
                sublabel=None,
                on_click=lambda e, c=child: self._enter(c.name or c._plain_name),
            ))

        if not dirs:
            self._list_view.controls.append(ft.Container(
                content=ft.Text(
                    t("picker.mtp_empty_folder"),
                    size=12,
                    color=theme.current.text_muted,
                    italic=True,
                ),
                padding=ft.Padding.all(12),
            ))

        self.page.update()

    # -- navigation actions -----------------------------------------------

    def _enter(self, name: str) -> None:
        self._path.append(name)
        self._render_current()

    def _go_up(self) -> None:
        if self._path:
            self._path.pop()
        if not self._path and self._device is not None:
            # Going up from storage list → re-render storages of same device
            self._render_current()
        else:
            self._render_current()

    # -- buttons -----------------------------------------------------------

    def _on_confirm(self, e: ft.ControlEvent) -> None:
        if self._device is None or not self._path:
            return
        # Windows -> mtp:// URI (MtpBackend); Linux -> gvfs path (LocalBackend).
        dest = build_destination(self._device, self._path)
        self.page.pop_dialog()
        self.on_select(dest)

    def _on_cancel(self, e: ft.ControlEvent) -> None:
        self.page.pop_dialog()

    # -- row helper --------------------------------------------------------

    def _row(
        self,
        *,
        icon,
        label: str,
        sublabel: str | None,
        on_click: Callable,
        muted: bool = False,
    ) -> ft.Control:
        th = theme.current
        title_color = th.text_muted if muted else th.text
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=th.text_muted if muted else th.primary, size=18),
                    ft.Column(
                        controls=[
                            ft.Text(label, size=13, color=title_color, weight=ft.FontWeight.W_500),
                        ] + (
                            [ft.Text(sublabel, size=10, color=th.text_muted, max_lines=1,
                                     overflow=ft.TextOverflow.ELLIPSIS)]
                            if sublabel else []
                        ),
                        spacing=1,
                        tight=True,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=th.text_muted, size=16),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=6,
            ink=True,
            on_click=on_click,
        )
