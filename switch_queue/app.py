"""
App — orchestrates state, builds the page, wires events.

The App class owns:
    - state (sources, games, dest, category order, copy status)
    - all stateful Flet control references (buttons, fields, progress bars,
      containers that get re-populated)
    - event handlers (add/remove source, start/pause/skip/cancel copy, etc.)

UI components (`ui/components/*.py`) and the layout (`ui/views/main_view.py`)
are pure — they take data and callbacks and return controls.
"""

from __future__ import annotations

import asyncio
import datetime
import queue
import threading
from pathlib import Path

import flet as ft

from .core import (
    LOG_DEBUG,
    LOG_ERROR,
    LOG_INFO,
    LOG_WARN,
    CopyEvent,
    CopyState,
    Game,
    GameFile,
    LogEntry,
    run_copy_queue,
    scan_source,
)
from .core.backends import is_mtp_uri
from .core.copier import make_backend
from .i18n import LANGUAGE_LABELS, set_locale, t
from .ui import theme
from .ui.components import build_log_panel, category_chips, game_row, source_card
from .ui.components.mtp_picker import MtpPicker
from .ui.theme import (
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from .ui.views import build_main_view
from .utils import clipboard as clipboard_util, fmt_eta, fmt_size

MAX_LOG_LINES = 1000
SHUTDOWN_GRACE_SECONDS = 30   # countdown shown before the actual shutdown fires


class App:
    """The single Flet app controller."""

    # ------------------------------------------------------------------ init

    def __init__(self, page: ft.Page) -> None:
        self.page = page

        # ---- State (set BEFORE building UI so _init_controls can read it) ----
        self.sources: list[Path] = []
        self.games: list[Game] = []
        self.category_order: list[str] = ["base", "update", "dlc"]
        self.dest_path: str = ""
        self.overwrite: bool = False
        self.cat_selected: str | None = None
        self.theme_mode: str = "dark"     # "dark" | "light"
        self.locale: str = "es"           # "es" | "en" — Spanish default
        self.expand_all: bool = False     # collapsed by default; collapsed header
                                          # already shows category counts and X/Y
        self.show_logs: bool = False      # logs drawer hidden by default
        self.logs: list[LogEntry] = []    # bounded by MAX_LOG_LINES

        # ---- "On finish" actions (settings dialog) ----
        self.notify_on_finish: bool = True       # desktop toast when done
        self.shutdown_on_finish: bool = False    # power off after success
        # id(game) -> bool. Remembers manual chevron toggles across rebuilds
        # (e.g. selecting a checkbox triggers a queue refresh; the user's
        # expanded games shouldn't snap shut).
        self.expanded_games: dict[int, bool] = {}

        # ---- Worker ----
        self.is_copying: bool = False
        self.copy_state = CopyState()
        self.copy_thread: threading.Thread | None = None

        # CopyEvents flow worker thread → queue → async poller → UI thread.
        # Calling page.update() directly from the worker thread on Flet 0.84
        # batches updates oddly and causes the progress bar to look frozen
        # until the queue completes. The poller drains every ~50ms and
        # flushes once per tick, which keeps the bar smooth.
        self._ui_queue: queue.Queue = queue.Queue()

        # ---- File picker (Service in Flet 0.84+; persists across rebuilds) ----
        self.file_picker = ft.FilePicker()
        page.services.append(self.file_picker)

        # ---- Initial render ----
        theme.set_mode(self.theme_mode)
        set_locale(self.locale)
        self._setup_page()
        self._init_controls()
        page.add(build_main_view(self))
        self._refresh_all()
        self.log_info(t("log.app_started"))
        page.update()

        # Start the UI queue poller (drains worker-thread CopyEvents into
        # the main thread).
        page.run_task(self._poll_ui_queue)

    def _setup_page(self) -> None:
        """Apply page-level chrome from the active theme."""
        p = self.page
        t = theme.current
        p.title = "Switch Queue Copy"
        p.theme_mode = ft.ThemeMode.DARK if t.name == "dark" else ft.ThemeMode.LIGHT
        p.bgcolor = t.bg
        p.theme = ft.Theme(
            color_scheme_seed=t.primary,
            visual_density=ft.VisualDensity.COMPACT,
            font_family="Segoe UI",
        )
        p.padding = 0
        p.window.width = WINDOW_WIDTH
        p.window.height = WINDOW_HEIGHT
        p.window.min_width = WINDOW_MIN_WIDTH
        p.window.min_height = WINDOW_MIN_HEIGHT

    def _init_controls(self) -> None:
        """Create (or re-create) every Flet control whose state we mutate later.

        Values are restored from `self.*` so a rebuild (theme/locale switch)
        preserves what the user already typed/checked.
        """
        th = theme.current

        # ---- Sources section ----
        self.sources_list = ft.Column(spacing=6)
        self.sources_empty = ft.Container(
            content=ft.Text(
                t("empty.no_sources"),
                size=13,
                color=th.text_muted,
                italic=True,
            ),
            padding=ft.Padding.symmetric(vertical=8, horizontal=4),
        )
        self.btn_add_folder = ft.FilledButton(
            content=t("btn.add_folder"),
            icon=ft.Icons.CREATE_NEW_FOLDER_ROUNDED,
            on_click=self._on_add_folder,
        )
        self.btn_add_many = ft.OutlinedButton(
            content=t("btn.add_many"),
            icon=ft.Icons.LIBRARY_ADD_ROUNDED,
            on_click=self._on_add_many,
        )
        self.btn_clear_sources = ft.OutlinedButton(
            content=t("btn.clear"),
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            on_click=self._on_clear_sources,
        )

        # ---- Destination section ----
        self.dest_field = ft.TextField(
            hint_text=t("field.dest_hint"),
            value=self.dest_path,
            on_change=self._on_dest_changed,
            border_color=th.border,
            focused_border_color=th.primary,
            color=th.text,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            text_size=13,
            expand=True,
        )
        self.btn_pick_dest = ft.OutlinedButton(
            content=t("btn.choose_local"),
            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
            on_click=self._on_pick_dest,
        )
        self.btn_pick_mtp = ft.OutlinedButton(
            content=t("btn.choose_mtp"),
            icon=ft.Icons.PHONELINK_ROUNDED,
            on_click=self._on_pick_mtp,
        )
        self.cb_overwrite = ft.Checkbox(
            label=t("field.overwrite"),
            value=self.overwrite,
            on_change=self._on_overwrite_changed,
        )

        # ---- Category order (lives inside the Settings dialog) ----
        self.cat_chips_holder = ft.Container(content=ft.Row())
        self.btn_cat_left = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            tooltip=t("tooltip.move_left"),
            on_click=lambda e: self._move_category(-1),
            icon_size=18,
        )
        self.btn_cat_right = ft.IconButton(
            icon=ft.Icons.ARROW_FORWARD_ROUNDED,
            tooltip=t("tooltip.move_right"),
            on_click=lambda e: self._move_category(1),
            icon_size=18,
        )

        # ---- AppBar buttons ----
        self.btn_toggle_logs = ft.IconButton(
            icon=ft.Icons.TERMINAL_ROUNDED,
            tooltip=t("tooltip.toggle_logs"),
            on_click=self._on_toggle_logs,
            icon_size=20,
        )
        self.btn_settings = ft.IconButton(
            icon=ft.Icons.SETTINGS_ROUNDED,
            tooltip=t("tooltip.settings"),
            on_click=self._on_open_settings,
            icon_size=20,
        )
        self.settings_dialog = self._build_settings_dialog()

        # ---- Logs drawer ----
        # We re-build the panel on every refresh; this holder lives forever
        # in the page tree and gets its `.content` swapped in place.
        self.log_panel_holder = ft.Container(visible=self.show_logs)

        # ---- Queue section ----
        self.queue_summary = ft.Text(t("status.no_games_yet"), size=12, color=th.text_muted)
        self.queue_list = ft.Column(spacing=4)
        self.queue_empty = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.INBOX_ROUNDED, size=36, color=th.border),
                    ft.Text(
                        t("empty.no_queue"),
                        size=13,
                        color=th.text_muted,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.Padding.symmetric(vertical=24),
            alignment=ft.Alignment.CENTER,
        )
        self.btn_mark_all = ft.TextButton(
            content=t("btn.mark_all"),
            icon=ft.Icons.CHECK_BOX_ROUNDED,
            on_click=lambda e: self._mark_all(True),
        )
        self.btn_unmark_all = ft.TextButton(
            content=t("btn.unmark_all"),
            icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK_ROUNDED,
            on_click=lambda e: self._mark_all(False),
        )
        self.btn_expand_all = ft.TextButton(
            content=t("btn.expand_all"),
            icon=ft.Icons.UNFOLD_MORE_ROUNDED,
            on_click=lambda e: self._set_expand_all(True),
        )
        self.btn_collapse_all = ft.TextButton(
            content=t("btn.collapse_all"),
            icon=ft.Icons.UNFOLD_LESS_ROUNDED,
            on_click=lambda e: self._set_expand_all(False),
        )

        # ---- Bottom progress bar ----
        self.status_text = ft.Text(t("status.ready"), size=12, color=th.text)
        self.speed_text = ft.Text("", size=11, color=th.text_muted, weight=ft.FontWeight.W_500)
        self.file_pb = ft.ProgressBar(value=0, bgcolor=th.progress_bg, color=th.primary, bar_height=4)
        self.global_pb = ft.ProgressBar(value=0, bgcolor=th.progress_bg, color=th.primary, bar_height=4)

        self.btn_start = ft.FilledButton(
            content=t("btn.start_copy"),
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            on_click=self._on_start_copy,
        )
        self.btn_pause = ft.OutlinedButton(
            content=t("btn.pause"),
            icon=ft.Icons.PAUSE_ROUNDED,
            on_click=self._on_toggle_pause,
            disabled=True,
        )
        self.btn_skip = ft.OutlinedButton(
            content=t("btn.skip_file"),
            icon=ft.Icons.SKIP_NEXT_ROUNDED,
            on_click=self._on_skip,
            disabled=True,
        )
        self.btn_cancel = ft.OutlinedButton(
            content=t("btn.cancel"),
            icon=ft.Icons.STOP_ROUNDED,
            on_click=self._on_cancel,
            disabled=True,
        )

    # ----------------------------------------------------- source handlers

    async def _on_add_folder(self, e: ft.ControlEvent) -> None:
        path = await self.file_picker.get_directory_path(
            dialog_title=t("picker.add_source_title")
        )
        if not path:
            return
        if self._add_source_path(Path(path), notify=True):
            self._refresh_all()

    def _add_source_path(self, raw: Path, *, notify: bool = True) -> bool:
        """Scan `raw`, append to sources/games, log + snackbar. Returns True on success.

        Shared between the single-folder picker and the multi-folder picker.
        """
        p = raw.resolve()
        if p in self.sources:
            if notify:
                self._snackbar(
                    t("snack.already_added_named", name=p.name) if "already_added_named" in self._t_keys() else t("snack.already_added"),
                    error=True,
                )
            return False
        try:
            new_games = scan_source(p)
        except Exception as exc:
            if notify:
                self._snackbar(t("snack.scan_error", error=str(exc)), error=True)
            self.log_error(t("snack.scan_error", error=str(exc)))
            return False
        if not new_games:
            if notify:
                self._snackbar(t("snack.no_games_detected"), error=True)
            return False
        self.sources.append(p)
        self.games.extend(new_games)
        if notify:
            if len(new_games) == 1:
                self._snackbar(t("snack.added_singular", name=p.name))
            else:
                self._snackbar(t("snack.added_plural", name=p.name, n=len(new_games)))
        self.log_info(t("log.source_added", name=p.name, n=len(new_games)))
        return True

    @staticmethod
    def _t_keys() -> set:
        """All known i18n keys in the current locale (used to feature-test)."""
        from .i18n import LOCALES, current_locale
        return set(LOCALES.get(current_locale, {}).keys())

    # -- Multi-source picker -----------------------------------------------

    async def _on_add_many(self, e: ft.ControlEvent) -> None:
        """Open the native multi-folder picker (Ctrl+Click multi-select).

        On Windows we drive ``IFileOpenDialog`` directly with the modern
        ``FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT`` flags via
        :mod:`switch_queue.utils.folder_picker`. The COM ``Show`` call
        blocks, so we run it on the default executor and await the result —
        the Flet UI keeps responding meanwhile.

        On non-Windows we fall back to our Flet-native checkbox modal
        (single-folder picker → list of subfolders → confirm), implemented
        in :meth:`_show_multi_select_dialog`.
        """
        import asyncio
        import sys

        from .utils import folder_picker

        if sys.platform == "win32":
            loop = asyncio.get_event_loop()

            def _show_native_dialog() -> list[Path]:
                return folder_picker.pick_folders(
                    title=t("picker.add_many_title"),
                )

            paths = await loop.run_in_executor(None, _show_native_dialog)
            if not paths:
                return  # cancelled or empty
            self._add_many_paths(paths)
            return

        # Non-Windows fallback (Flet custom modal)
        parent_str = await self.file_picker.get_directory_path(
            dialog_title=t("picker.add_many_parent_title")
        )
        if not parent_str:
            return
        parent = Path(parent_str).resolve()
        try:
            subs = sorted(
                [d for d in parent.iterdir() if d.is_dir()],
                key=lambda x: x.name.lower(),
            )
        except OSError as exc:
            self._snackbar(t("snack.cant_list_parent", error=str(exc)), error=True)
            return
        if not subs:
            self._snackbar(t("snack.no_subfolders"), error=True)
            return
        self._show_multi_select_dialog(parent, subs)

    def _add_many_paths(self, paths: list[Path]) -> None:
        """Apply a list of selected paths as sources (notify once at end)."""
        added = 0
        for path in paths:
            if self._add_source_path(path, notify=False):
                added += 1
        self._refresh_all()
        total = len(paths)
        if added == total:
            self._snackbar(t("snack.added_many", n=added, total=total))
        else:
            self._snackbar(t("snack.added_many_partial", n=added, total=total))

    def _show_multi_select_dialog(self, parent: Path, subfolders: list[Path]) -> None:
        """Render the multi-folder picker modal and wire its confirm action."""
        th = theme.current

        # One Checkbox per subfolder, default all checked. Mapping the
        # control to its Path lets the confirm handler harvest selection.
        checks: dict[str, tuple[Path, ft.Checkbox]] = {}
        count_text = ft.Text(
            "", size=11, color=th.text_muted, weight=ft.FontWeight.W_500,
        )

        def update_count():
            n = sum(1 for _p, c in checks.values() if c.value)
            count_text.value = t("picker.add_many_count", n=n, total=len(checks))
            try:
                self.page.update()
            except Exception:
                pass

        rows: list[ft.Control] = []
        for sub in subfolders:
            cb = ft.Checkbox(value=True, on_change=lambda _e: update_count())
            checks[str(sub)] = (sub, cb)
            rows.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            cb,
                            ft.Icon(ft.Icons.FOLDER_ROUNDED, color=th.primary, size=16),
                            ft.Text(
                                sub.name, size=13, color=th.text,
                                expand=True, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=2),
                )
            )

        list_view = ft.Column(
            controls=rows, spacing=2,
            scroll=ft.ScrollMode.AUTO, height=360,
        )

        def select_all(_e):
            for _p, c in checks.values():
                c.value = True
            update_count()

        def deselect_all(_e):
            for _p, c in checks.values():
                c.value = False
            update_count()

        def cancel(_e):
            self.page.pop_dialog()

        def confirm(_e):
            chosen = [p for p, c in checks.values() if c.value]
            self.page.pop_dialog()
            if chosen:
                self._add_many_paths(chosen)

        actions_row = ft.Row(
            controls=[
                ft.TextButton(
                    content=t("btn.select_all"),
                    icon=ft.Icons.CHECK_BOX_ROUNDED,
                    on_click=select_all,
                ),
                ft.TextButton(
                    content=t("btn.deselect_all"),
                    icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK_ROUNDED,
                    on_click=deselect_all,
                ),
                ft.Container(expand=True),
                count_text,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        body = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        str(parent), size=11, color=th.text_muted,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    actions_row,
                    ft.Container(
                        content=list_view,
                        bgcolor=th.surface_2,
                        border=ft.Border.all(1, th.border),
                        border_radius=8,
                        padding=ft.Padding.all(4),
                    ),
                ],
                spacing=10,
                tight=True,
            ),
            width=560,
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=th.surface,
            title=ft.Text(
                t("picker.add_many_title"), size=16,
                weight=ft.FontWeight.W_600, color=th.text,
            ),
            content=body,
            actions=[
                ft.TextButton(content=t("btn.cancel"), on_click=cancel),
                ft.FilledButton(
                    content=t("btn.add_selected"),
                    icon=ft.Icons.ADD_ROUNDED,
                    on_click=confirm,
                ),
            ],
        )
        self.page.show_dialog(dlg)
        update_count()

    def _on_clear_sources(self, e: ft.ControlEvent) -> None:
        if not self.sources:
            return
        self.sources.clear()
        self.games.clear()
        self.expanded_games.clear()
        self.log_info(t("log.sources_cleared"))
        self._refresh_all()

    def _remove_source(self, root: Path) -> None:
        self.sources = [p for p in self.sources if p != root]
        self.games = [g for g in self.games if g.source_root != root]
        # Drop any per-game expansion entries that no longer exist.
        live_ids = {id(g) for g in self.games}
        self.expanded_games = {k: v for k, v in self.expanded_games.items() if k in live_ids}
        self.log_info(t("log.source_removed", name=root.name))
        self._refresh_all()

    # ------------------------------------------------ destination handlers

    async def _on_pick_dest(self, e: ft.ControlEvent) -> None:
        path = await self.file_picker.get_directory_path(dialog_title=t("picker.dest_title"))
        if path:
            self.dest_path = path
            self.dest_field.value = path
            self.page.update()
            self._update_button_states()

    def _on_pick_mtp(self, e: ft.ControlEvent) -> None:
        """Open the Flet-native MTP picker. The selected URI ends up in
        ``dest_path`` and the field shows it (mtp://Switch/...)."""
        def on_select(uri: str) -> None:
            self.dest_path = uri
            self.dest_field.value = uri
            self.log_info(t("log.dest_mtp", uri=uri))
            self.page.update()
            self._update_button_states()

        picker = MtpPicker(self.page, on_select=on_select)
        picker.show()

    def _on_dest_changed(self, e: ft.ControlEvent) -> None:
        self.dest_path = (e.control.value or "").strip()
        self._update_button_states()

    def _on_overwrite_changed(self, e: ft.ControlEvent) -> None:
        self.overwrite = bool(e.control.value)

    # ------------------------------------------------------- settings dialog

    def _build_settings_dialog(self) -> ft.AlertDialog:
        """Build the modal settings dialog from the current theme + locale."""
        th = theme.current

        # ----- Appearance: theme switch + language dropdown
        self.theme_switch = ft.Switch(
            value=(self.theme_mode == "dark"),
            label=t("field.dark_mode"),
            on_change=self._on_theme_changed,
        )

        # ----- "On finish" toggles
        self.notify_switch = ft.Switch(
            value=self.notify_on_finish,
            label=t("field.notify_on_finish"),
            on_change=self._on_notify_changed,
        )
        self.shutdown_switch = ft.Switch(
            value=self.shutdown_on_finish,
            label=t("field.shutdown_on_finish"),
            on_change=self._on_shutdown_changed,
        )
        self.language_dropdown = ft.Dropdown(
            label=t("field.language"),
            value=self.locale,
            options=[
                ft.DropdownOption(key=code, text=label)
                for code, label in LANGUAGE_LABELS.items()
            ],
            on_select=self._on_language_changed,
            border_color=th.border,
            focused_border_color=th.primary,
            color=th.text,
            text_size=13,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            width=240,
        )

        appearance_title = ft.Text(
            t("section.appearance"),
            size=11,
            weight=ft.FontWeight.W_700,
            color=th.text_muted,
        )

        # ----- Category order
        order_title = ft.Text(
            t("section.category_order"),
            size=11,
            weight=ft.FontWeight.W_700,
            color=th.text_muted,
        )
        order_row = ft.Row(
            controls=[
                self.cat_chips_holder,
                ft.Container(expand=True),
                self.btn_cat_left,
                self.btn_cat_right,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        order_help = ft.Text(
            t("help.order"),
            size=11,
            color=th.text_muted,
        )

        # ----- On-finish section
        finish_title = ft.Text(
            t("section.on_finish"),
            size=11,
            weight=ft.FontWeight.W_700,
            color=th.text_muted,
        )
        finish_help = ft.Text(
            t("help.on_finish"),
            size=11,
            color=th.text_muted,
        )

        body = ft.Container(
            content=ft.Column(
                controls=[
                    appearance_title,
                    self.theme_switch,
                    self.language_dropdown,
                    ft.Divider(color=th.border, height=20),
                    order_title,
                    order_row,
                    order_help,
                    ft.Divider(color=th.border, height=20),
                    finish_title,
                    self.notify_switch,
                    self.shutdown_switch,
                    finish_help,
                ],
                spacing=10,
                tight=True,
            ),
            width=480,
        )
        return ft.AlertDialog(
            modal=True,
            bgcolor=th.surface,
            title=ft.Text(
                t("dialog.settings_title"),
                size=16,
                weight=ft.FontWeight.W_600,
                color=th.text,
            ),
            content=body,
            actions=[ft.TextButton(t("btn.close"), on_click=self._on_close_settings)],
        )

    def _on_open_settings(self, e: ft.ControlEvent) -> None:
        # Reset chip selection every time the dialog opens.
        self.cat_selected = None
        self._refresh_categories()
        self._update_button_states()
        self.page.show_dialog(self.settings_dialog)

    def _on_close_settings(self, e: ft.ControlEvent) -> None:
        self.cat_selected = None
        self.page.pop_dialog()
        self._refresh_categories()
        self._refresh_queue()
        self._update_button_states()

    def _on_theme_changed(self, e: ft.ControlEvent) -> None:
        new_mode = "dark" if e.control.value else "light"
        if new_mode == self.theme_mode:
            return
        self.theme_mode = new_mode
        self.log_info(t("log.theme_changed", mode=new_mode))
        self._reopen_settings_after_rebuild()

    def _on_notify_changed(self, e: ft.ControlEvent) -> None:
        self.notify_on_finish = bool(e.control.value)
        self.log_info(
            t("log.setting_changed",
              name=t("field.notify_on_finish"),
              value=self._yes_no(self.notify_on_finish))
        )

    def _on_shutdown_changed(self, e: ft.ControlEvent) -> None:
        self.shutdown_on_finish = bool(e.control.value)
        self.log_info(
            t("log.setting_changed",
              name=t("field.shutdown_on_finish"),
              value=self._yes_no(self.shutdown_on_finish))
        )

    @staticmethod
    def _yes_no(b: bool) -> str:
        return t("common.yes") if b else t("common.no")

    def _on_language_changed(self, e: ft.ControlEvent) -> None:
        new_locale = e.control.value or self.locale
        if new_locale == self.locale:
            return
        self.locale = new_locale
        self.log_info(t("log.locale_changed", locale=LANGUAGE_LABELS.get(new_locale, new_locale)))
        self._reopen_settings_after_rebuild()

    def _reopen_settings_after_rebuild(self) -> None:
        """Common path for theme/locale switches: close, rebuild, reopen settings."""
        try:
            self.page.pop_dialog()
        except Exception:
            pass
        self._rebuild()
        # Re-open settings so the user sees the result immediately.
        self.page.show_dialog(self.settings_dialog)

    # ----------------------------------------------------------- rebuild

    def _rebuild(self) -> None:
        """Tear down and reconstruct the page with the active theme + locale.

        Preserves user state (sources, games, dest path, overwrite flag, etc.)
        because those live on `self.*` and are read back by `_init_controls`.
        The FilePicker (page.services) is not touched.
        """
        theme.set_mode(self.theme_mode)
        set_locale(self.locale)
        self.page.controls.clear()
        self._setup_page()
        self._init_controls()
        self.page.add(build_main_view(self))
        self._refresh_all()
        self.page.update()

    # ---------------------------------------------------------- logs drawer

    def log(self, level: str, message: str) -> None:
        """Append a single line to the in-app log drawer."""
        self.logs.append(LogEntry(datetime.datetime.now(), level, message))
        if len(self.logs) > MAX_LOG_LINES:
            self.logs = self.logs[-MAX_LOG_LINES:]
        self._refresh_log_panel()

    def log_info(self, msg: str) -> None:  self.log(LOG_INFO, msg)
    def log_warn(self, msg: str) -> None:  self.log(LOG_WARN, msg)
    def log_error(self, msg: str) -> None: self.log(LOG_ERROR, msg)
    def log_debug(self, msg: str) -> None: self.log(LOG_DEBUG, msg)

    def _refresh_log_panel(self) -> None:
        """Rebuild the panel control if it's currently visible.

        While hidden we **skip the rebuild + page.update** entirely — entries
        live in ``self.logs`` and we only flush them to the panel when the
        user toggles it open. This keeps a busy queue (which logs many lines)
        from triggering one full Flet update per log entry, which on a deep
        layout (57 games with category chips) caused the queue to flicker or
        not render at all.
        """
        if not hasattr(self, "log_panel_holder") or not self.show_logs:
            return
        self.log_panel_holder.content = build_log_panel(
            entries=self.logs,
            on_clear=self._on_clear_logs,
            on_copy=self._on_copy_logs,
            on_close=self._on_toggle_logs,
            visible=True,
        )
        self.log_panel_holder.visible = True
        try:
            self.page.update()
        except Exception:
            pass

    def _on_toggle_logs(self, e: ft.ControlEvent | None = None) -> None:
        self.show_logs = not self.show_logs
        if self.show_logs:
            # Build the panel from the buffered entries the first time we
            # show it (or after toggling closed → open).
            self.log_panel_holder.content = build_log_panel(
                entries=self.logs,
                on_clear=self._on_clear_logs,
                on_copy=self._on_copy_logs,
                on_close=self._on_toggle_logs,
                visible=True,
            )
        self.log_panel_holder.visible = self.show_logs
        try:
            self.page.update()
        except Exception:
            pass

    def _on_clear_logs(self) -> None:
        self.logs.clear()
        self._refresh_log_panel()

    def _on_copy_logs(self) -> None:
        text = "\n".join(
            f"[{e.timestamp.strftime('%H:%M:%S')}] {e.level.upper():<5} {e.message}"
            for e in self.logs
        )
        # See switch_queue/utils/clipboard.py for why we don't use Flet's
        # async clipboard or a tkinter window: this hits Win32 directly.
        if clipboard_util.set_text(text):
            self._snackbar(t("logs.copied"))
        else:
            self.log_error("Clipboard copy failed (Win32 SetClipboardData returned 0)")
            self._snackbar(t("logs.copied_failed"), error=True)

    # ----------------------------------------------------- category handlers

    def _move_category(self, delta: int) -> None:
        if self.cat_selected is None:
            return
        idx = self.category_order.index(self.cat_selected)
        new_idx = idx + delta
        if not (0 <= new_idx < len(self.category_order)):
            return
        self.category_order[idx], self.category_order[new_idx] = (
            self.category_order[new_idx],
            self.category_order[idx],
        )
        self._refresh_categories()
        self._refresh_queue()
        self._update_button_states()

    def _select_category(self, cat: str) -> None:
        # Toggle: clicking the already-selected chip deselects it.
        self.cat_selected = None if self.cat_selected == cat else cat
        self._refresh_categories()
        self._update_button_states()

    # ---------------------------------------------------- game/file handlers

    def _toggle_game(self, game: Game) -> None:
        if self.is_copying:
            return
        new = not game.selected
        game.selected = new
        for f in game.files:
            f.selected = new
        self._refresh_queue()
        self._update_button_states()

    def _toggle_file(self, game: Game, gf: GameFile) -> None:
        if self.is_copying:
            return
        gf.selected = not gf.selected
        game.selected = any(f.selected for f in game.files)
        self._refresh_queue()
        self._update_button_states()

    def _move_game(self, game: Game, delta: int) -> None:
        if self.is_copying:
            return
        idx = self.games.index(game)
        new_idx = idx + delta
        if not (0 <= new_idx < len(self.games)):
            return
        self.games[idx], self.games[new_idx] = self.games[new_idx], self.games[idx]
        self._refresh_queue()

    def _remove_game(self, game: Game) -> None:
        """Drop a single game from the queue (does not touch any files on disk).

        The game's source folder stays in the Origen list — only this entry
        is removed. To bring it back, re-add the source folder.
        """
        if self.is_copying:
            return
        if game in self.games:
            self.games.remove(game)
            self.log_info(t("log.game_removed", name=game.name))
        # Drop the removed game's expansion entry.
        self.expanded_games.pop(id(game), None)
        # Keep source cards in sync (count drops; if it was the last game from
        # that source, the count badge will read "0 juegos").
        self._refresh_sources()
        self._refresh_queue()
        self._update_button_states()

    def _mark_all(self, value: bool) -> None:
        if self.is_copying:
            return
        for g in self.games:
            g.selected = value
            for f in g.files:
                f.selected = value
        self._refresh_queue()
        self._update_button_states()

    def _set_expand_all(self, value: bool) -> None:
        if self.is_copying:
            return
        self.expand_all = value
        # Bulk action wins — forget per-game manual toggles.
        self.expanded_games.clear()
        self._refresh_queue()

    def _on_game_expanded(self, game: Game, expanded: bool) -> None:
        """Track manual chevron clicks so refreshes don't reset them."""
        self.expanded_games[id(game)] = expanded

    # --------------------------------------------------------------- refresh

    def _refresh_all(self) -> None:
        self._refresh_sources()
        self._refresh_categories()
        self._refresh_queue()
        self._update_button_states()
        self.page.update()

    def _refresh_sources(self) -> None:
        self.sources_list.controls.clear()
        for src in self.sources:
            n = sum(1 for g in self.games if g.source_root == src)
            self.sources_list.controls.append(
                source_card(
                    src=src,
                    game_count=n,
                    on_remove=self._remove_source,
                    disabled=self.is_copying,
                )
            )
        self.sources_empty.visible = not self.sources

    def _refresh_categories(self) -> None:
        self.cat_chips_holder.content = category_chips(
            order=self.category_order,
            selected=self.cat_selected,
            on_select=self._select_category,
        )

    def _ordered_files(self, game: Game) -> list[GameFile]:
        order = {c: i for i, c in enumerate(self.category_order)}
        return sorted(
            game.files,
            key=lambda f: (order.get(f.category, 99), f.rel.name.lower()),
        )

    def _refresh_queue(self) -> None:
        self.queue_list.controls.clear()
        if not self.games:
            self.queue_summary.value = t("status.no_games_yet")
            self.queue_empty.visible = True
            return
        self.queue_empty.visible = False

        sel_count = sum(1 for g in self.games if g.selected for f in g.files if f.selected)
        sel_size = sum(f.size for g in self.games if g.selected for f in g.files if f.selected)
        total_count = sum(len(g.files) for g in self.games)
        total_size = sum(f.size for g in self.games for f in g.files)
        self.queue_summary.value = t(
            "summary.queue",
            sel_count=sel_count,
            total_count=total_count,
            sel_size=fmt_size(sel_size),
            total_size=fmt_size(total_size),
        )

        for idx, game in enumerate(self.games):
            # Per-game memory wins over the global default.
            expanded = self.expanded_games.get(id(game), self.expand_all)
            self.queue_list.controls.append(
                game_row(
                    game=game,
                    idx=idx,
                    total=len(self.games),
                    ordered_files=self._ordered_files(game),
                    on_toggle_game=self._toggle_game,
                    on_toggle_file=self._toggle_file,
                    on_move=self._move_game,
                    on_remove=self._remove_game,
                    on_expand_change=self._on_game_expanded,
                    is_copying=self.is_copying,
                    expanded=expanded,
                )
            )

    # -------------------------------------------------------- button states

    def _update_button_states(self) -> None:
        not_copying = not self.is_copying
        has_games = bool(self.games)
        has_selected_files = any(
            g.selected and any(f.selected for f in g.files) for g in self.games
        )
        has_dest = bool(self.dest_path.strip())

        self.btn_add_folder.disabled = not not_copying
        self.btn_add_many.disabled = not not_copying
        self.btn_clear_sources.disabled = (not self.sources) or (not not_copying)
        self.btn_pick_dest.disabled = not not_copying
        self.btn_pick_mtp.disabled = not not_copying
        self.dest_field.disabled = not not_copying
        self.cb_overwrite.disabled = not not_copying

        self.btn_mark_all.disabled = (not has_games) or (not not_copying)
        self.btn_unmark_all.disabled = (not has_games) or (not not_copying)
        self.btn_expand_all.disabled = (not has_games) or (not not_copying)
        self.btn_collapse_all.disabled = (not has_games) or (not not_copying)

        if self.cat_selected is None:
            self.btn_cat_left.disabled = True
            self.btn_cat_right.disabled = True
        else:
            cat_idx = self.category_order.index(self.cat_selected)
            self.btn_cat_left.disabled = (cat_idx == 0) or (not not_copying)
            self.btn_cat_right.disabled = (
                cat_idx == len(self.category_order) - 1
            ) or (not not_copying)

        self.btn_start.disabled = not (has_games and has_selected_files and has_dest and not_copying)
        self.page.update()

    # ----------------------------------------------------------- snackbars

    def _snackbar(self, msg: str, error: bool = False) -> None:
        t = theme.current
        bgcolor = t.snack_err_bg if error else t.snack_ok_bg
        fgcolor = t.snack_err_fg if error else t.snack_ok_fg
        snack = ft.SnackBar(
            content=ft.Text(msg, color=fgcolor, weight=ft.FontWeight.W_500),
            bgcolor=bgcolor,
            duration=2500,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        self.page.show_dialog(snack)

    # ---------------------------------------------------------------- copy

    def _build_queue(self) -> list[tuple[Game, GameFile]]:
        out: list[tuple[Game, GameFile]] = []
        for game in self.games:
            if not game.selected:
                continue
            for gf in self._ordered_files(game):
                if gf.selected:
                    out.append((game, gf))
        return out

    def _on_start_copy(self, e: ft.ControlEvent) -> None:
        dest_str = self.dest_path.strip()
        if not dest_str:
            self._snackbar(t("snack.specify_dest"), error=True)
            return

        if not is_mtp_uri(dest_str):
            # Local destination: validate path and create folder eagerly so
            # any permission/disk error surfaces before the queue starts.
            dst = Path(dest_str)
            try:
                dst.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                self.log_error(str(exc))
                self._snackbar(t("snack.cant_create_dest", error=str(exc)), error=True)
                return
            for src in self.sources:
                if src.resolve() == dst.resolve():
                    self._snackbar(t("snack.same_src_dst"), error=True)
                    return
            self.log_info(t("log.dest_local", path=str(dst)))
            destination: object = dst
        else:
            # MTP: resolve the backend NOW so disconnection / missing device
            # is caught before we even build the confirm dialog.
            try:
                destination = make_backend(dest_str)
            except Exception as exc:
                self.log_error(t("log.mtp_unavailable", error=str(exc)))
                self._snackbar(t("snack.mtp_unavailable"), error=True)
                return
            self.log_info(t("log.mtp_connected", name=dest_str))

        queue = self._build_queue()
        if not queue:
            self._snackbar(t("snack.no_files_selected"), error=True)
            return

        total_bytes = sum(gf.size for _, gf in queue)

        def do_start(_e):
            self.page.pop_dialog()
            self._launch_copy(queue, destination)

        def do_cancel(_e):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("dialog.confirm_copy_title")),
            content=ft.Text(
                t("dialog.confirm_copy_body", n=len(queue), size=fmt_size(total_bytes))
            ),
            actions=[
                ft.TextButton(t("btn.cancel"), on_click=do_cancel),
                ft.FilledButton(t("btn.start"), on_click=do_start),
            ],
        )
        self.page.show_dialog(dlg)

    def _launch_copy(
        self,
        queue: list[tuple[Game, GameFile]],
        destination: "str | Path",
    ) -> None:
        self.copy_state.cancel_event.clear()
        self.copy_state.pause_event.clear()
        self.copy_state.skip_event.clear()
        self.is_copying = True

        self.btn_pause.disabled = False
        self.btn_pause.content = t("btn.pause")
        self.btn_pause.icon = ft.Icons.PAUSE_ROUNDED
        self.btn_skip.disabled = False
        self.btn_cancel.disabled = False
        self._update_button_states()
        self._refresh_queue()
        self.page.update()

        self.page.run_thread(
            run_copy_queue,
            queue,
            destination,
            self.overwrite,
            self.copy_state,
            self._on_copy_event,
        )

    def _on_copy_event(self, ev: CopyEvent) -> None:
        """Called from the worker thread — just enqueue. UI updates happen
        on the main thread via the async poller (`_poll_ui_queue`)."""
        self._ui_queue.put(ev)

    async def _poll_ui_queue(self) -> None:
        """Drain worker CopyEvents into the UI thread.

        Runs forever. Every 50 ms it applies *all* queued events and issues
        a single ``page.update()`` so the renderer doesn't thrash.
        """
        while True:
            await asyncio.sleep(0.05)
            applied = False
            while True:
                try:
                    ev = self._ui_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    self._apply_copy_event(ev)
                    applied = True
                except Exception as exc:  # never let one bad event kill the loop
                    self.log_error(f"UI event handler error: {exc}")
            if applied:
                try:
                    self.page.update()
                except Exception:
                    pass

    def _apply_copy_event(self, ev: CopyEvent) -> None:
        """Apply a CopyEvent to the UI. Called from the main (UI) thread."""
        kind = ev.kind
        p = ev.payload
        if kind == "queue_start":
            self.global_pb.value = 0
            self.file_pb.value = 0
            self.status_text.value = t(
                "status.copying_n",
                n=p["total_files"],
                size=fmt_size(p["total_bytes"]),
            )
            self.log_info(t("log.queue_started", n=p["total_files"], size=fmt_size(p["total_bytes"])))
        elif kind == "item_start":
            game: Game = p["game"]
            gf: GameFile = p["file"]
            label = t(
                "status.current",
                i=p["idx"] + 1,
                n=p["total"],
                cat=gf.category.upper(),
                game=game.name,
                file=gf.rel.name,
            )
            self.status_text.value = label
            self.file_pb.value = 0
            # Surface the current file at INFO so the logs panel shows it
            # in real time (was DEBUG-only before, hidden in noise).
            self.log_info(label)
        elif kind == "item_progress":
            ft_total = max(p["file_total"], 1)
            self.file_pb.value = p["file_done"] / ft_total
            tt = max(p["total_bytes"], 1)
            self.global_pb.value = p["total_done"] / tt
            speed = p["speed"]
            eta = p["eta"]
            if speed > 0:
                self.speed_text.value = f"{fmt_size(speed)}/s   ·   ETA {fmt_eta(eta)}"
            else:
                self.speed_text.value = ""
        elif kind == "item_done":
            r = p["result"]
            f: GameFile = p["file"]
            if r == "skip-existing":
                self.status_text.value = t("status.skip_existing", name=f.rel.name)
                self.log_info(t("log.item_skip_existing", name=f.rel.name))
            elif r == "skip-manual":
                self.status_text.value = t("status.skipped", name=f.rel.name)
                self.log_warn(t("log.item_skip_manual", name=f.rel.name))
            elif r == "error":
                self.status_text.value = t("status.error_file", name=f.rel.name)
                self.log_error(t("log.item_error", name=f.rel.name))
            elif r == "ok":
                self.log_debug(t("log.item_ok", name=f.rel.name))
        elif kind == "queue_done":
            self.is_copying = False
            self.speed_text.value = ""
            self.btn_pause.disabled = True
            self.btn_pause.content = t("btn.pause")
            self.btn_pause.icon = ft.Icons.PAUSE_ROUNDED
            self.btn_skip.disabled = True
            self.btn_cancel.disabled = True
            if p["result"] == "completed":
                self.global_pb.value = 1.0
                self.file_pb.value = 1.0
                ok = p.get("ok_count", 0)
                err = p.get("error_count", 0)
                skipped = p.get("skip_count", 0)
                total_bytes = p["total_bytes"]
                size = fmt_size(total_bytes)

                # Always log the full breakdown for debugging.
                self.log_info(t("log.queue_completed",
                                ok=ok, errors=err, skipped=skipped, size=size))

                if ok == 0 and err > 0:
                    # Nothing actually copied — surface as error, don't lie.
                    self.status_text.value = t("status.completed_zero")
                    self._snackbar(t("snack.copy_done_zero"), error=True)
                elif err > 0:
                    self.status_text.value = t(
                        "status.completed_with_errors",
                        errors=err, ok=ok, skipped=skipped,
                    )
                    self._snackbar(t("snack.copy_done_errors", errors=err), error=True)
                else:
                    self.status_text.value = t("status.completed_size", size=size)
                    self._snackbar(t("snack.copy_done"))

                # Side-effects (desktop notification, optional shutdown).
                self._on_finish(ok_count=ok, error_count=err, total_size=total_bytes)
            else:
                self.status_text.value = t("status.cancelled")
                self.log_warn(t("log.queue_cancelled"))
                self._snackbar(t("snack.copy_cancelled"))
            self._update_button_states()
            self._refresh_queue()
        elif kind == "error":
            # core's `error` event carries a pre-formatted message string.
            # Forward it as-is — it includes the path/exception detail.
            self.status_text.value = p["message"]
            self.log_error(p["message"])
        # NOTE: no page.update() here. _poll_ui_queue issues exactly one
        # per tick after applying everything queued.

    # ------------------------------------------------------ on-finish hooks

    def _on_finish(self, *, ok_count: int, error_count: int, total_size: int) -> None:
        """Run side-effects after a queue finishes successfully.

        Notification fires regardless of error count (so the user knows the
        run is done either way). Shutdown only fires on a clean run — if
        anything errored we'd rather leave the machine awake to investigate.
        """
        if self.notify_on_finish:
            self._notify_done(ok_count=ok_count, error_count=error_count, total_size=total_size)

        if self.shutdown_on_finish and error_count == 0 and ok_count > 0:
            self._schedule_shutdown()

    def _notify_done(self, *, ok_count: int, error_count: int, total_size: int) -> None:
        """Pop a desktop toast (Windows / macOS / Linux via plyer)."""
        title = t("notify.title")
        if error_count > 0:
            msg = t("notify.done_with_errors", ok=ok_count, errors=error_count)
        elif ok_count == 0:
            msg = t("notify.done_zero")
        else:
            msg = t("notify.done_ok", size=fmt_size(total_size))

        # Desktop toast (best effort).
        try:
            from plyer import notification as plyer_notification
            plyer_notification.notify(
                title=title,
                message=msg,
                app_name="Switch Queue Copy",
                timeout=10,
            )
        except Exception as exc:
            self.log_warn(f"Desktop notification failed: {exc}")

        # Always beep on Windows — works without any deps.
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    def _schedule_shutdown(self) -> None:
        """Show an in-app modal countdown before triggering Windows shutdown.

        UX choice: relying only on Windows' built-in 60 s shutdown dialog
        is risky — it pops on the system level which the user might miss
        if they're focused on another window. Our dialog is right on top
        of our app, the countdown ticks visibly, and the cancel button is
        big and obvious. Only when the countdown hits 0 do we actually
        invoke ``shutdown /s /t 0``.
        """
        import sys
        if sys.platform != "win32":
            self.log_warn("Shutdown is supported on Windows only.")
            return

        # Per-shutdown cancel signal. Lives only as long as the countdown.
        cancel_event = asyncio.Event()
        th = theme.current

        countdown_text = ft.Text(
            t("shutdown.countdown", seconds=SHUTDOWN_GRACE_SECONDS),
            size=14,
            weight=ft.FontWeight.W_700,
            color=th.danger,
        )

        def on_cancel(_e):
            cancel_event.set()
            self.page.pop_dialog()
            self.log_info(t("shutdown.cancelled"))
            self._snackbar(t("shutdown.cancelled"))

        def on_now(_e):
            cancel_event.set()        # stop the countdown task
            self.page.pop_dialog()
            self._do_shutdown_now()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=th.surface,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.POWER_SETTINGS_NEW_ROUNDED, color=th.danger, size=22),
                    ft.Text(
                        t("shutdown.dialog_title"),
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=th.text,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(t("shutdown.dialog_body"), size=12, color=th.text_muted),
                        countdown_text,
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=440,
            ),
            actions=[
                # Cancel is the primary action — bigger, filled, default focus.
                ft.FilledButton(
                    content=t("btn.cancel_shutdown"),
                    icon=ft.Icons.CLOSE_ROUNDED,
                    on_click=on_cancel,
                ),
                ft.TextButton(
                    content=t("btn.shutdown_now"),
                    icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED,
                    on_click=on_now,
                ),
            ],
        )
        self.page.show_dialog(dlg)
        self.log_warn(t("shutdown.scheduled_with_countdown", seconds=SHUTDOWN_GRACE_SECONDS))

        # Drive the countdown from the UI loop. ``asyncio.Event`` lets the
        # cancel/now buttons interrupt it cleanly.
        self.page.run_task(self._shutdown_countdown, cancel_event, countdown_text)

    async def _shutdown_countdown(self, cancel_event: asyncio.Event, countdown_text: ft.Text) -> None:
        """Tick the countdown text once per second; fire shutdown if it expires."""
        for remaining in range(SHUTDOWN_GRACE_SECONDS, 0, -1):
            if cancel_event.is_set():
                return
            countdown_text.value = t("shutdown.countdown", seconds=remaining)
            try:
                self.page.update()
            except Exception:
                pass
            await asyncio.sleep(1.0)

        if cancel_event.is_set():
            return
        # Reached zero without interaction → power off.
        try:
            self.page.pop_dialog()
        except Exception:
            pass
        self._do_shutdown_now()

    def _do_shutdown_now(self) -> None:
        """Invoke Windows shutdown immediately. Logs but doesn't snackbar
        (user is about to lose the window anyway)."""
        import subprocess
        try:
            subprocess.Popen(
                ["shutdown", "/s", "/t", "0"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.log_warn(t("shutdown.firing_now"))
        except Exception as exc:
            self.log_error(f"Shutdown command failed: {exc}")

    # ------------------------------------------------------------------ pause

    def _on_toggle_pause(self, e: ft.ControlEvent) -> None:
        if self.copy_state.pause_event.is_set():
            self.copy_state.pause_event.clear()
            self.btn_pause.content = t("btn.pause")
            self.btn_pause.icon = ft.Icons.PAUSE_ROUNDED
            self.log_info(t("log.copy_resumed"))
        else:
            self.copy_state.pause_event.set()
            self.btn_pause.content = t("btn.resume")
            self.btn_pause.icon = ft.Icons.PLAY_ARROW_ROUNDED
            self.log_info(t("log.copy_paused"))
        self.page.update()

    def _on_skip(self, e: ft.ControlEvent) -> None:
        self.copy_state.skip_event.set()

    def _on_cancel(self, e: ft.ControlEvent) -> None:
        def confirm(_e):
            self.page.pop_dialog()
            self.copy_state.cancel_event.set()
            self.copy_state.pause_event.clear()

        def cancel(_e):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("dialog.cancel_copy_title")),
            content=ft.Text(t("dialog.cancel_copy_body")),
            actions=[
                ft.TextButton(t("btn.keep_copying"), on_click=cancel),
                ft.FilledButton(t("btn.cancel"), on_click=confirm),
            ],
        )
        self.page.show_dialog(dlg)
