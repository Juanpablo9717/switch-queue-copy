# Switch Queue Copy

A serial file-copy tool for Nintendo Switch libraries (`.nsp` / `.nsz` / `.xci`),
with **strict in-order execution**, **automatic classification** into
BASE / UPDATE / DLC, and **native MTP destinations** (Switch consoles in
DBI/Tinfoil install mode, Android phones, etc.).

Built with [Flet](https://flet.dev) (Material 3 / Flutter desktop).

![Material 3 minimalist UI with category tag chips, multi-source list, sticky progress bar](assets/screenshot.png)

---

## Why this exists

The Windows file-copy dialog has a problem: if you paste a 5 GB file and
then paste a 100 MB one, both transfers happen **in parallel** and the
small one finishes first. That's fine for photos, terrible for a Switch
library where the **base** game *must* arrive before the **update**
before the **DLC**, and where a single 4 GB update can blow your SD card
write cache if it's racing with three other transfers.

This app implements an actual queue: **one file at a time**, in the
order *you* want, with proper progress, pause, skip, cancel.

---

## Features

- **Multi-source.** Add any number of folders. Each is auto-detected as
  a single game, a library (parent folder with many games), a collection
  (Trine Collection / SteamWorld Collection), or a flat bundle (ACA
  NEOGEO Metal Slug 1–X with all six games in one folder).
- **Multi-folder picker.** Native Windows `IFileOpenDialog` with
  `FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT` — Ctrl+Click and Shift+Click
  to pick many folders in one go. Falls back to a Flet checkbox modal
  on non-Windows.
- **Auto-classification.** Every `.nsp` / `.nsz` / `.xci` is tagged
  BASE / UPDATE / DLC using the Switch Title ID convention plus
  folder/filename hints. See [How classification works](#how-classification-works).
- **Flat-bundle splitting.** A folder containing files for several
  *distinct* games (different Title IDs) splits into one queue entry
  per game, named from the filename. Examples: ACA NEOGEO bundles,
  Mario Galaxy 1+2 packs.
- **Structural mod detection.** Any folder shipping an
  `atmosphere/contents/` subdir is treated as a CFW mod and skipped —
  regardless of how it's named (catches "Russian Machine Translation
  (24.05.2025)" and friends).
- **Tree view by default.** Each game is an expandable card showing
  its files, with category-count chips visible while collapsed
  (`[BASE·1] [UPDATE·1] [DLC·5]`).
- **Reorderable.** Per-game ↑/↓ buttons; per-category global priority
  (BASE → UPDATE → DLC by default) reorderable in Settings.
- **Selective.** Tick/untick whole games or individual files.
- **Pause / Skip / Cancel** mid-copy. Works against both filesystem and
  MTP destinations.
- **Live speed and ETA**, 3-second moving average. Smooth progress
  thanks to a UI poller (50 ms) that drains worker-thread events.
- **Resumable.** Destination files with matching size are skipped
  (toggle "Sobrescribir si ya existe" to force).
- **Strictly serial — and tested.** See
  [`tests/test_copier.py`](tests/test_copier.py): an explicit invariant
  proves no two files are ever in flight at the same time.
- **Dark / Light theme** (dark default), **i18n** (Spanish / English),
  **in-app log drawer** (VS Code-style terminal panel with copy-to-clipboard
  via Win32 SetClipboardData), **MTP destinations** (Windows only),
  **desktop notification + optional shutdown** when the queue finishes
  (with a 30 s in-app countdown to abort).

---

## Prerequisites

- **Python ≥ 3.10** ([download](https://www.python.org/downloads/)). Make
  sure `python` is on your PATH (the installer asks; tick it).
- **git** ([download](https://git-scm.com/download/win)) — to clone the repo.
- **Windows 10/11** if you want MTP destinations (Switch via DBI/Tinfoil,
  Android phones, etc.). The rest works on Linux/macOS too.
- *(optional)* a virtual environment tool like `venv` (ships with Python).

Disk: ~150 MB during install (Flet runtime cache ~50 MB on first run,
package wheels ~80 MB, your venv).

## Dependencies

| Package | Min version | Why |
| --- | --- | --- |
| `flet` | 0.84 (< 1.0) | UI framework (Material 3 over Flutter) |
| `comtypes` | 1.4 | Windows COM bindings for MTP / WPD and `IFileOpenDialog` (Windows-only — installed conditionally via `sys_platform == "win32"`) |
| `plyer` | 2.1 | Cross-platform desktop notifications |
| **`pytest`** *(dev)* | 8 | Test runner |

All locked through [`pyproject.toml`](pyproject.toml). When you do
`pip install -e ".[dev]"` you get everything in one shot.

Optional at runtime: nothing else. The Heribert17 MTP code is vendored
under `switch_queue/vendor/` (MIT) — no separate install needed.

## Install + run

```bash
# 1. Clone
git clone https://github.com/Juanpablo9717/switch-queue-copy.git
cd switch-queue-copy

# 2. Virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate              # Windows (cmd / powershell)
# source .venv/bin/activate         # Linux / macOS

# 3. Editable install with dev extras
pip install -e ".[dev]"

# 4. Launch
python -m switch_queue
```

The **first launch** downloads the Flet desktop runtime (~50 MB,
one-time). After that the app opens in <1 s.

## Test

```bash
python -m pytest -v          # all 40 tests, ~1 s
python -m pytest tests/test_copier.py -v       # one file
python -m pytest -k "serial" -v                 # by name
```

What the suite covers:

- **Classification** — every regex rule, including 7 real-world filenames
  from a Switch dump.
- **Scanner** — single game, library, nested collection, flat bundle
  splitting, DLC subfolders, mod skipping (by name *and* by structure),
  empty folders.
- **Copy queue serial invariant** — proves no two files are ever in
  flight at the same time via event-log analysis. The test that
  matters most.
- **Pause / Skip / Cancel** during a running copy (with a shrunk
  `COPY_BUF` so the timing is reproducible).
- **Skip-existing / Overwrite** behaviour.
- **Win32 clipboard round-trip** — writes, reads back via the same
  API, asserts equality.
- **`os.path.join` regression test for MTP paths** with drive-letter-looking
  storage names like `5: SD Card install`.

## Build a standalone Windows `.exe`

```powershell
.\scripts\build_exe.ps1
```

The script:

1. Sanity-checks that `flet` CLI is on PATH (errors if not — install via `pip install flet`).
2. Cleans previous `dist/` and `build/`.
3. Runs `flet pack switch_queue/__main__.py --name "Switch Queue Copy"`
   under the hood, which invokes **PyInstaller** + bundles the Flutter
   runtime + your venv's site-packages.
4. Optionally picks up `assets/icon.ico` if present.

Output: **`dist/Switch Queue Copy.exe`** — a single ~80 MB executable.
No installer, no DLLs alongside; copy it anywhere and double-click.

For your own releases, the typical flow is: tag a version (`git tag
v0.1.0 && git push --tags`), then upload the `.exe` to the GitHub
Releases page as a download.

Note: PyInstaller bundles need to match the target OS — a `.exe` built
on Windows runs on Windows only.

## Quick reference (cheat sheet)

```bash
cd switch-queue-copy
pip install -e ".[dev]"                # one-time
python -m switch_queue                  # run
python -m pytest -v                     # test
.\scripts\build_exe.ps1                 # build dist/*.exe
```

---

## Project structure

```
switch_queue/
├── __main__.py              ← `python -m switch_queue` entrypoint
├── app.py                   ← App class: state + handlers + control refs
│
├── core/                    ← Domain logic. Zero UI imports.
│   ├── models.py            ← Game, GameFile, CopyEvent, CopyState, LogEntry
│   ├── classifier.py        ← classify_file() + regex
│   ├── scanner.py           ← scan_source() + mod / bundle detection
│   ├── copier.py            ← run_copy_queue() — the serial worker
│   └── backends/
│       ├── base.py          ← DestinationBackend protocol
│       ├── local.py         ← LocalBackend (open + shutil + 4 MB buffer)
│       └── mtp.py           ← MtpBackend (Heribert17/mtp + progress wrapper)
│
├── ui/                      ← Flet view layer
│   ├── theme.py             ← Light/Dark Theme dataclasses + globals
│   ├── components/          ← Pure builder functions (data → ft.Control)
│   │   ├── tag_chip.py
│   │   ├── category_count_chip.py
│   │   ├── category_chips.py
│   │   ├── source_card.py
│   │   ├── game_row.py
│   │   ├── mtp_picker.py
│   │   └── log_panel.py
│   └── views/
│       └── main_view.py     ← Top-level page composition
│
├── utils/
│   ├── format.py            ← fmt_size, fmt_eta
│   ├── clipboard.py         ← Win32 SetClipboardData via ctypes
│   └── folder_picker.py     ← Native IFileOpenDialog with multi-select
│
├── i18n/                    ← Tiny translator with es.py + en.py dicts
│   ├── translator.py
│   ├── es.py
│   └── en.py
│
└── vendor/                  ← Third-party code we needed to ship locally
    └── heribert17_mtp/      ← Windows WPD bindings (MIT). Stripped down
                              to just win_access.py + LICENSE.

tests/
├── conftest.py              ← shared touch() helper
├── test_classifier.py       ← every regex rule, 7 real-world filenames
├── test_scanner.py          ← single game / library / collection / bundle / mod
├── test_copier.py           ← serial invariant + pause/skip/cancel
├── test_skip_existing.py    ← resumable semantics
├── test_clipboard.py        ← Win32 clipboard round-trip
└── test_mtp_path_safety.py  ← regression for the os.path.join landmine

scripts/
└── build_exe.ps1            ← one-click flet pack → dist/Switch Queue Copy.exe
```

---

## Architecture (data flow)

```
                  ┌─────────────────────────────────────────────────────┐
                  │                       App (Flet)                    │
                  │                                                     │
                  │   ┌────────────────────────────────────────────┐    │
   user click ───►│   │  ui/components/* + ui/views/main_view.py   │    │
                  │   │   (pure builder fns — re-renders happen    │    │
                  │   │    by replacing parent.content)            │    │
                  │   └─────────────┬──────────────────────────────┘    │
                  │                 │ events                            │
                  │                 ▼                                   │
                  │   ┌────────────────────────────────────────────┐    │
                  │   │   app.py handlers (sync or async)          │    │
                  │   │   • mutate self.sources / self.games       │    │
                  │   │   • call _refresh_all() → page.update()    │    │
                  │   └─────────────┬──────────────────────────────┘    │
                  │                 │                                   │
                  └─────────────────┼───────────────────────────────────┘
                                    │
                  scan? ─────────────┼───── copy?
                                    │
                  ┌─────────────────▼──────┐         ┌─────────────────┐
                  │     core.scanner       │         │  core.copier    │
                  │   walks source paths   │         │  serial for-loop│
                  │   → list[Game]         │         │  picks Backend  │
                  └────────────────────────┘         │  emits events   │
                                                     └────────┬────────┘
                                                              │
                                            ┌─────────────────┼──────────────────┐
                                            ▼                                    ▼
                                   ┌────────────────┐                   ┌────────────────┐
                                   │ LocalBackend   │                   │  MtpBackend    │
                                   │ open/shutil    │                   │ WPD COM via    │
                                   │ 4 MB buffer    │                   │ Heribert17     │
                                   │ progress every │                   │ + custom stream│
                                   │ buffer read    │                   │ wrapper for    │
                                   │                │                   │ live progress  │
                                   └────────────────┘                   └────────────────┘
```

Worker thread emits `CopyEvent`s (queue_start, item_start, item_progress,
item_done, queue_done, error). The App polls them every 50 ms from an
asyncio task and updates Flet controls + calls `page.update()` once per tick.
This avoids the worker thread touching the Flet UI directly (which
sometimes leads to dropped repaints / flicker).

---

## Design decisions

These are the trade-offs that shape the codebase. If you're picking it up
to extend, read this first — it'll tell you *why* things are arranged the
way they are.

### Why Flet over Qt / Tkinter / wxPython

Tried Tkinter first — it works but caps out aesthetically (no real
rounded corners, no SVG icons, no widgets-in-Treeview-cells). Qt is
nicer but a heavy install and the licensing for distribution is awkward
on commercial bundles.

Flet renders via Flutter, gives us Material 3 controls (real chips,
real icons, animations) for a single pip install. The trade-off: 60 MB
runtime bundle, and the API churned across versions (this codebase
targets **Flet 0.84** specifically — `ft.Padding.symmetric(...)`,
`page.show_dialog(...)`, `ft.Clipboard` as a `Service`, etc.).

### Why a custom serial worker instead of `asyncio` / `concurrent.futures`

The product requirement is *strictly* one file at a time. A `for` loop
in a single thread is the most boring, most provable way to guarantee
that — no executors, no semaphores, no race surface. See
[`tests/test_copier.py::test_no_two_files_in_flight_at_once`](tests/test_copier.py)
for the regression test that asserts this from the event log.

### Why vendor Heribert17/mtp instead of `pip install`-ing it

`Heribert17/mtp` exists on GitHub but its `setup.py` expects a `src/`
layout that doesn't match the repo, so `pip install git+https://...`
fails during wheel build. We vendor just the file we need
(`win_access.py`, ~900 lines, MIT) under
[`switch_queue/vendor/heribert17_mtp/`](switch_queue/vendor/heribert17_mtp/)
with its LICENSE and an attribution note. `comtypes` is the only runtime
dep added.

### Why ctypes for the clipboard, not Flet's `Clipboard` or Tkinter

Two wrong paths first:
- `page.clipboard.set(text)` is **async** in Flet 0.84. Calling it from
  a sync handler returns the coroutine without ever awaiting — silent
  no-op. The snackbar said "copied", clipboard was untouched.
- Tkinter's `clipboard_append` relies on Tk *owning a window* while the
  data is on the clipboard. Destroy the Tk root and Windows often
  releases the data immediately.

Solution in [`switch_queue/utils/clipboard.py`](switch_queue/utils/clipboard.py):
direct `user32.SetClipboardData` via ctypes. `SetClipboardData` transfers
a global-memory handle to the OS, which then owns it — no window
dependency, fully synchronous. Round-trip tested in
[`tests/test_clipboard.py`](tests/test_clipboard.py).

### Why a custom IFileOpenDialog wrapper for multi-folder picking

Flet's `get_directory_path` uses the legacy "Browse for Folder" dialog
which is **single-select**. The modern Windows `IFileOpenDialog`
supports `FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT` (Ctrl+Click / Shift+Click
multi-select) but Flet doesn't expose those flags.

[`switch_queue/utils/folder_picker.py`](switch_queue/utils/folder_picker.py)
drives the COM API directly via `comtypes` — defines the vtables for
`IShellItem`, `IShellItemArray`, `IFileDialog`, `IFileOpenDialog`, and
invokes the dialog on a worker thread via `loop.run_in_executor` so
the Flet UI keeps responding while the modal is up.

### Why MTP needs its own backend (and how it preserves mid-file pause/skip/cancel)

`open(dst, "wb")` doesn't work for MTP paths — they live in the Windows
Shell namespace, not the filesystem. We need WPD COM calls.

The trick that preserves byte-level progress and mid-file control:
Heribert17's `_upload_stream` repeatedly calls
`inputstream.read(blocksize)` until empty. We wrap the input file with a
`_ProgressStream` that:
- counts bytes returned and emits progress on each block;
- honors `pause_event` / `cancel_event` / `skip_event` between reads;
- raises a private exception to abort cleanly — leaving the partial
  object un-`Commit`ed and then deleting it via `IShellItem.Delete()`.

See [`switch_queue/core/backends/mtp.py::_ProgressStream`](switch_queue/core/backends/mtp.py).

### Why we walk the device manually instead of calling Heribert17's `makedirs`

`Heribert17.makedirs` builds paths with `os.path.join`. On Windows,
`os.path.join("DeviceName", "5: SD Card install")` treats `5:` as a drive
letter and **discards** the first arg — leaving a 1-component path the
library then refuses. DBI numbers all its install storages `"1:"`, `"2:"`,
`"5: SD Card install"`, etc., so every upload to a Switch hit this wall.

Our `MtpBackend._walk_to(parts: list[str])` never builds a string path —
it walks `get_child` / `create_content` step by step. Regression test in
[`tests/test_mtp_path_safety.py`](tests/test_mtp_path_safety.py).

### Why per-game expansion state is kept in a dict keyed by `id(game)`

The queue rebuilds when you tick a checkbox or reorder. Without a
sticky state, every interaction would collapse open games. We track
`self.expanded_games: dict[int, bool]` keyed by Python `id()` of the
`Game` object — survives rebuilds, gets cleared when the underlying
Game is removed, and is wiped by the bulk "Expand all / Collapse all"
buttons.

### Why categories are ordered globally, not per-game

The user asked for the simpler model and we kept it. The `[↑] [↓]`
buttons on each game row reorder games among each other (not the
categories within a game). Category priority is a single global list
in Settings, applied to every game's file ordering at render time.

### Why log entries are stored in memory only

In-app log drawer is for debugging the current session — not a forensic
audit log. Capped at 1000 lines (oldest dropped). For persistent logs
we'd add an opt-in file sink to `LogEntry` writes; not implemented.

### Why we always go through `theme.current` instead of importing constants

So that `set_mode("dark")` followed by a UI rebuild reads the new
palette. Imports like `from .theme import SURFACE` would capture the
string at import time and never refresh. Every component does
`th = theme.current` at the top of its builder function.

---

## How classification works

Files are matched against three rules **in order**:

1. **Folder hint.** If any parent folder matches `^(\d+\s*)?DLC\b`
   (e.g. `DLC/`, `7 DLC/`, `12 DLC/`), the file is DLC.
2. **Filename hint.** If the filename contains `[DLC ...]`, it's DLC.
3. **Title ID.** A 16-hex Title ID in brackets:
   - last 3 chars `000` → **BASE**
   - last 3 chars `800` → **UPDATE**
   - anything else → **DLC**

### Flat-bundle splitting

Within a folder, files are grouped by **first 12 hex chars** of their
Title IDs. If a single folder produces more than one group, each group
becomes its own Game entry in the queue (named from the longest common
filename prefix before the first `[`). This handles ACA NEOGEO bundles
and similar.

- Base/Update share all 13 leading hex chars.
- DLCs share the first 12 but differ at position 12.
- Truly unrelated games differ by position 11 or earlier.

So 12 is the right prefix length to keep a game's base + update + DLCs
together while splitting unrelated games apart.

### Mod skipping (two layers)

- **By name:** any path component matching `\bmod\b` or `atmosphere`
  (case-insensitive).
- **By structure:** any folder containing `atmosphere/contents/`. This
  catches mods with neutral names like "Russian Machine Translation
  (24.05.2025)" that ship Atmosphère CFW payloads + patched updates.

---

## MTP usage

Some destinations don't have a drive letter — they're MTP / WPD devices
exposed by Windows: a Switch console running DBI / Tinfoil in MTP
install mode, Android phones, cameras. Standard `open()` / `shutil`
can't write to those.

**To use:**

1. Connect the device. It should show up under *This PC* in Explorer
   (e.g. "Switch") *without* a drive letter.
2. In the app, click **Dispositivo MTP** next to the destination field.
3. Pick the device → storage → folder. The destination is stored as a
   URI like `mtp://Switch/5: SD Card install`.
4. Press **Iniciar copia**. Files are streamed via the WPD COM API.

### Trade-offs vs. local destinations

- Speed is limited by MTP itself (~30–60 MB/s typical) — about 4× slower
  than a card reader. Card reader is faster but doesn't trigger DBI's
  auto-install, so MTP wins for that workflow.
- Mid-file pause/skip/cancel works (we wrap the input stream and abort
  cleanly), but expect a small delay until the current MTP block flushes.
- File-existence-by-size works on most stacks; some MTP firmwares report
  stale sizes. Use **Sobrescribir si ya existe** if you hit that.

---

## Known limitations & edge cases

- **MTP is Windows-only.** The `comtypes` + WPD stack doesn't exist on
  Linux / macOS. The destination picker hides the "Dispositivo MTP"
  button on non-Windows.
- **MTP delete-after-failed-upload may leave a stub** on some firmwares.
  If you see a 0-byte file in the destination after a cancel, delete it
  manually from Explorer.
- **Logs are in-memory.** Closing the app loses them. Use 📋 to copy
  before quitting if you need them.
- **The `.exe` is ~80 MB** because PyInstaller bundles the Flet runtime.
  This is normal.
- **Shutdown setting only fires on a clean run.** `error_count > 0` or
  `ok_count == 0` skips the shutdown even if the toggle is on — we'd
  rather leave the PC awake to investigate than reboot away from a
  failure.
- **Per-game expansion state resets on theme/locale change.** The
  full-page rebuild on theme switch drops the `expanded_games` dict.
  Acceptable tradeoff vs. tracking state across full re-renders.

---

## Where to look when X breaks

| Symptom | First file to open |
| --- | --- |
| Scanner picks up wrong files / wrong classification | [`switch_queue/core/scanner.py`](switch_queue/core/scanner.py), [`switch_queue/core/classifier.py`](switch_queue/core/classifier.py) |
| A copy fails silently | Open the in-app log drawer (`>_` icon top-right), look for ERROR / WARN lines. They map back to [`switch_queue/core/copier.py`](switch_queue/core/copier.py) emission points. |
| MTP says "device not found" | [`switch_queue/core/backends/mtp.py::_resolve_device`](switch_queue/core/backends/mtp.py). Refresh from the picker forces a `RefreshDeviceList` COM call. |
| Progress bar jumps at the end | The MTP block size is large (some firmwares use 16+ MB blocks). Workaround would be a separate progress tick from a timer thread; not implemented. |
| UI doesn't reflect a state change | Look for the missing `self.page.update()` in the handler. The `_refresh_*` family is the established pattern. |
| Clipboard "succeeded" but nothing pasted | You're on a non-Windows fallback or running stale `__pycache__`. Clean: `rm -rf __pycache__ */__pycache__ */*/__pycache__`. |
| A new test fails after refactor | Check the serial invariant first (`test_no_two_files_in_flight_at_once`). If that passes, the bug is local. |

---

## Extending the app

### Add a new language

Three steps, doesn't touch the rest of the code:

1. Create `switch_queue/i18n/<code>.py` exporting a `TRANSLATIONS` dict
   with the same keys as `es.py` / `en.py`. Missing keys fall back to
   Spanish, then to the key itself.
2. Register it in [`switch_queue/i18n/translator.py`](switch_queue/i18n/translator.py):
   ```python
   from . import en, es, pt
   LOCALES = {"es": es.TRANSLATIONS, "en": en.TRANSLATIONS, "pt": pt.TRANSLATIONS}
   LANGUAGE_LABELS = {"es": "Español", "en": "English", "pt": "Português"}
   ```
3. The Settings dialog dropdown rebuilds from `LANGUAGE_LABELS` — no UI
   changes needed.

### Add a new destination backend

Implement the protocol in [`switch_queue/core/backends/base.py`](switch_queue/core/backends/base.py):

```python
class DestinationBackend(Protocol):
    def make_dirs(self, rel_path: Path) -> None: ...
    def file_exists_with_size(self, rel_path: Path, filename: str, expected: int) -> bool: ...
    def remove_partial(self, rel_path: Path, filename: str) -> None: ...
    def upload(
        self, src: Path, rel_path: Path, filename: str, size: int,
        state: CopyState, on_progress: Callable[[int], None],
    ) -> str: ...  # RESULT_OK | RESULT_CANCEL | RESULT_SKIP | RESULT_ERROR
```

Add a URI detector to [`switch_queue/core/copier.py::make_backend`](switch_queue/core/copier.py)
and you're done — the copier doesn't care.

Reference implementations: `LocalBackend` (open/shutil) and `MtpBackend`
(WPD).

### Add a new on-finish action

Hook into [`switch_queue/app.py::_on_finish`](switch_queue/app.py).
Add a toggle to `_build_settings_dialog`, a state attr in `__init__`,
read it inside `_on_finish` and act. The notification + shutdown actions
are the patterns to copy.

### Add a new component

Drop a `ui/components/<name>.py` exporting a pure function `data → ft.Control`.
Theme tokens via `from .. import theme` then `theme.current.*`. Import
once in [`switch_queue/ui/components/__init__.py`](switch_queue/ui/components/__init__.py).

---

## License

MIT — see [LICENSE](LICENSE).

Third-party:
- [Heribert17/mtp](https://github.com/Heribert17/mtp) (MIT, vendored under `switch_queue/vendor/`).
- [Flet](https://flet.dev) (Apache 2.0).
- [plyer](https://github.com/kivy/plyer) (MIT).
- [comtypes](https://github.com/enthought/comtypes) (MIT).
