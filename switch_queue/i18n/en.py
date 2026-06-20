"""English translations."""

TRANSLATIONS = {
    # ----- App / sections -----
    "app.title": "Switch Queue Copy",
    "section.source": "Source",
    "section.dest": "Destination",
    "section.queue": "Queue",
    "section.appearance": "Appearance",
    "section.category_order": "Category order",
    "section.on_finish": "When finished",

    # ----- Buttons -----
    "btn.add_folder": "Add folder",
    "btn.add_many": "Add several…",
    "btn.add_selected": "Add selected",
    "btn.select_all": "Check all",
    "btn.deselect_all": "Uncheck all",
    "btn.clear": "Clear",
    "btn.choose": "Browse",
    "btn.start_copy": "Start copy",
    "btn.pause": "Pause",
    "btn.resume": "Resume",
    "btn.skip_file": "Skip file",
    "btn.cancel": "Cancel",
    "btn.mark_all": "Select all",
    "btn.unmark_all": "Deselect all",
    "btn.expand_all": "Expand all",
    "btn.collapse_all": "Collapse all",
    "btn.close": "Close",
    "btn.start": "Start",
    "btn.keep_copying": "Keep copying",
    "btn.choose_here": "Choose here",
    "btn.choose_local": "Local folder",
    "btn.choose_mtp": "MTP device",

    # ----- Field labels / hints -----
    "field.dest_hint": "Destination folder",
    "field.overwrite": "Overwrite if it already exists",
    "field.dark_mode": "Dark mode",
    "field.language": "Language",
    "field.notify_on_finish": "Show notification when done",
    "field.shutdown_on_finish": "Shut down PC when done",

    # ----- Tooltips -----
    "tooltip.settings": "Settings",
    "tooltip.move_left": "Move left",
    "tooltip.move_right": "Move right",
    "tooltip.move_up": "Move up",
    "tooltip.move_down": "Move down",
    "tooltip.remove_source": "Remove this folder",
    "tooltip.remove_game": "Remove this game from queue",
    "tooltip.refresh": "Refresh",

    # ----- File picker dialog titles -----
    "picker.add_source_title": "Add source folder",
    "picker.dest_title": "Destination folder",
    "picker.add_many_parent_title": "Choose a parent folder",
    "picker.add_many_title": "Choose folders to add",
    "picker.add_many_count": "{n} of {total} selected",
    "picker.mtp_title": "Choose MTP destination",
    "picker.mtp_breadcrumb_root": "Connected devices",
    "picker.mtp_no_devices": "No MTP devices detected. Connect the device and refresh.",
    "picker.mtp_enum_error": "Error enumerating devices: {error}",
    "picker.mtp_install_hint": "MTP unavailable: install the GVFS-MTP backend (gvfs-mtp on Arch/Fedora, gvfs-backends on Debian/Ubuntu) and reconnect the device.",
    "picker.mtp_empty_folder": "(empty folder)",
    "picker.mtp_go_up": "Go up one level",

    # ----- Snackbars -----
    "snack.already_added": "That folder is already added.",
    "snack.already_added_named": "'{name}' is already in the list.",
    "snack.no_subfolders": "That folder has no subfolders.",
    "snack.cant_list_parent": "Can't read folder: {error}",
    "snack.added_many": "Added {n} folders.",
    "snack.added_many_partial": "Added {n} of {total} (others were empty or already loaded).",
    "snack.scan_error": "Scan failed: {error}",
    "snack.no_games_detected": "No .nsp/.nsz/.xci files detected in that folder.",
    "snack.added_singular": "Added: {name}  →  1 game.",
    "snack.added_plural": "Added: {name}  →  {n} games.",
    "snack.specify_dest": "Set a destination first.",
    "snack.cant_create_dest": "Can't create destination: {error}",
    "snack.same_src_dst": "Source and destination are the same.",
    "snack.no_files_selected": "No files selected.",
    "snack.copy_done": "Copy completed without errors.",
    "snack.copy_done_errors": "Copy finished with {errors} errors. Check the logs.",
    "snack.copy_done_zero": "No files were copied. Check the logs.",
    "snack.copy_cancelled": "Copy cancelled.",

    # ----- Dialogs -----
    "dialog.confirm_copy_title": "Confirm copy",
    "dialog.confirm_copy_body": "{n} files will be copied ({size}).\nStart?",
    "dialog.cancel_copy_title": "Cancel copy",
    "dialog.cancel_copy_body": "Cancel the in-progress queue?",
    "dialog.settings_title": "Settings",

    # ----- Status / queue area -----
    "status.ready": "Ready.",
    "status.no_games_yet": "Not scanned yet.",
    "status.copying_n": "Copying {n} files · {size}",
    "status.cancelled_by_user": "Cancelled by the user.",
    "status.cancelled": "Cancelled.",
    "status.completed_size": "Completed · {size} copied.",
    "status.completed_with_errors": "Completed with {errors} errors ({ok} OK · {skipped} skipped).",
    "status.completed_zero": "Queue finished without copying anything (all failed or skipped).",
    "status.skip_existing": "Skipped (already exists): {name}",
    "status.skipped": "Skipped: {name}",
    "status.error_file": "Error: {name}",
    "status.current": "[{i}/{n}]  {cat} · {game} / {file}",

    # ----- Empty / placeholders -----
    "empty.no_sources": "No folders added yet.",
    "empty.no_queue": "Add a folder above to see the queue.",

    # ----- Help text -----
    "help.order": (
        "The leftmost copies first. "
        "Click a tag to select it, then use ← → to move it."
    ),
    "help.on_finish": (
        "When 'Shut down PC' is on, finishing the queue opens a confirm "
        "dialog with a 30s countdown. Click Cancel to abort — otherwise "
        "the PC powers off."
    ),

    # ----- Notifications + shutdown -----
    "notify.title": "Switch Queue Copy",
    "notify.done_ok": "Copy completed — {size} copied.",
    "notify.done_with_errors": "Copy finished with {errors} errors ({ok} OK).",
    "notify.done_zero": "Queue finished without copying any files.",
    "shutdown.dialog_title": "Shut down PC?",
    "shutdown.dialog_body": (
        "The queue finished without errors. Your PC will shut down when the "
        "countdown reaches zero. If you're using it, cancel now."
    ),
    "shutdown.countdown": "Shutting down in {seconds} seconds…",
    "shutdown.cancelled": "Shutdown cancelled.",
    "shutdown.scheduled_with_countdown": "Shutdown scheduled: {seconds}s countdown started.",
    "shutdown.firing_now": "Triggering system shutdown…",
    "btn.cancel_shutdown": "Cancel shutdown",
    "btn.shutdown_now": "Shut down now",

    # ----- Generic -----
    "common.yes": "ON",
    "common.no": "OFF",
    "log.setting_changed": "Setting '{name}' → {value}.",

    # ----- Small labels -----
    "label.archivo": "File",
    "label.cola": "Queue",
    "label.juego": "game",
    "label.juegos": "games",

    # ----- Queue summary -----
    "summary.queue": "{sel_count} / {total_count} files · {sel_size} / {total_size}",

    # ----- Logs panel -----
    "logs.title": "Logs",
    "logs.empty": "(no events yet)",
    "logs.clear": "Clear logs",
    "logs.copy": "Copy to clipboard",
    "logs.close": "Hide logs",
    "logs.toggle": "Show logs",
    "logs.copied": "Logs copied to clipboard.",
    "logs.copied_failed": "Could not copy logs to clipboard.",
    "tooltip.toggle_logs": "Show / hide logs",

    # ----- Log lines (preformatted) -----
    "log.app_started": "App started.",
    "log.theme_changed": "Theme set to {mode}.",
    "log.locale_changed": "Language set to {locale}.",
    "log.source_added": "Source added: {name} ({n} games).",
    "log.source_removed": "Source removed: {name}.",
    "log.sources_cleared": "All sources removed.",
    "log.game_removed": "Game removed from queue: {name}.",
    "log.dest_local": "Local destination: {path}.",
    "log.dest_mtp": "MTP destination: {uri}.",
    "log.queue_started": "Queue started: {n} files · {size}.",
    "log.queue_completed": "Queue completed: {ok} OK, {errors} errors, {skipped} skipped ({size}).",
    "log.queue_cancelled": "Queue cancelled by user.",
    "log.item_ok": "OK · {name}",
    "log.item_skip_existing": "Skipped (exists) · {name}",
    "log.item_skip_manual": "Skipped by user · {name}",
    "log.item_error": "Error · {name}",
    "log.copy_paused": "Copy paused.",
    "log.copy_resumed": "Copy resumed.",
    "log.mtp_unavailable": "MTP device unavailable: {error}",
    "log.mtp_connected": "MTP device found: {name}",

    # ----- MTP errors -----
    "snack.mtp_unavailable": "MTP device not detected. Check the connection.",
}
