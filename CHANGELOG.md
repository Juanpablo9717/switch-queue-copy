# Changelog

All notable changes to **Switch Queue Copy** are documented here.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

> **How to use this file**
>
> - The `[Unreleased]` block at the top is a **running journal**. When
>   you (or another agent) push a change to `main`, add a one-liner
>   under the matching subsection (`Added`, `Changed`, `Fixed`,
>   `Removed`, `Security`).
> - When the maintainer decides to cut a release, the `[Unreleased]`
>   block is renamed to `[X.Y.Z] – YYYY-MM-DD` and a fresh empty
>   `[Unreleased]` is added on top. The tag `vX.Y.Z` is then pushed and
>   the CI publishes the binaries.
> - **Do not edit historical entries.** Once a version is released, its
>   block is frozen.

---

## [Unreleased]

### Added
- _(nothing yet)_

### Changed
- _(nothing yet)_

### Fixed
- _(nothing yet)_

### Removed
- _(nothing yet)_

---

## [0.2.0] – 2026-06-20

### Added
- **MTP destinations on Linux** via the desktop's gvfs layer (`gio`).
  New `LinuxMtpBackend` copies with `gio copy` — which sends each file
  with its size up front (like Windows WPD), so **DBI install over MTP
  works on Linux**, verified on a real Switch. Picker enumerates and
  browses gvfs-mounted devices; install storages receive files flat,
  ordinary storages keep the source folder structure. Pause maps to
  `SIGSTOP`/`SIGCONT`, cancel/skip to process termination, progress to
  parsing `gio copy -p`. No new Python dependency (shells out to `gio`).
  Requires `gvfs-mtp` (Arch/Fedora) / `gvfs-backends` (Debian/Ubuntu);
  the picker shows an install hint when absent.
- `docs/linux-mtp.md` documenting the Linux MTP design, the KDE
  device-contention caveat, and troubleshooting.
- `tests/test_mtp_linux.py` — pure unit tests for the gvfs provider
  (mock `gio`, no device needed).

### Changed
- MTP picker is now platform-dispatched (`mtp_provider`): Windows keeps
  the WPD/COM backend unchanged; Linux uses the new gvfs path. On
  Windows the chosen destination stays an `mtp://` URI; on Linux it's an
  `mtp://<gvfs-host>/…` URI routed to `LinuxMtpBackend`.

---

## [0.1.0] – 2026-05-18

First public release.

### Added

- **Multi-source folder picker** with auto-detection of layout:
  single game folder, library, nested collection (Trine / SteamWorld),
  flat multi-game bundle (e.g. ACA NEOGEO Metal Slug 1–X).
- **Native Windows multi-folder dialog** via `IFileOpenDialog`
  (`FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT`) — Ctrl+Click /
  Shift+Click to pick many folders in one go.
- **Automatic file classification** into BASE / UPDATE / DLC based on
  the Switch Title ID convention plus folder/filename hints.
- **Flat-bundle splitting**: a folder mixing files for multiple
  distinct games is split into one queue entry per game, named from
  the longest common filename prefix.
- **Structural mod detection**: any folder shipping an
  `atmosphere/contents/` subdirectory is treated as a CFW mod and
  skipped regardless of name (catches "Russian Machine Translation"
  packs).
- **Serial copy queue** with pause / skip / cancel. Tested strictly:
  no two files are ever in flight at the same time.
- **Local filesystem destination** with 4 MB buffer + `shutil.copystat`
  metadata preservation.
- **MTP / WPD destination** on Windows. Streams via Heribert17's WPD
  bindings (vendored) wrapped in a custom progress stream that
  preserves byte-level progress and mid-file pause / skip / cancel.
- **Live speed and ETA** via a 3-second moving average.
- **Resumable copies**: destination files with matching size are
  skipped (toggle "Sobrescribir si ya existe" to force).
- **Material 3 UI** built on Flet: dark mode by default with light
  toggle, ES / EN i18n with dropdown switch, category tag chips
  (Ant Design style), per-game expansion memory, in-app log drawer
  with Win32 clipboard copy.
- **Settings dialog** with reorderable category priority (BASE →
  UPDATE → DLC default) and on-finish actions: desktop notification
  (plyer) + optional Windows shutdown with 30 s in-app countdown.
- **Test suite**: 40 pytest tests including the strict-serial
  invariant for the copy queue and a Win32 clipboard round-trip.
- **GitHub Actions** for CI (Windows + Linux × Python 3.10 + 3.12)
  and tag-triggered releases (Windows .exe + Linux binary).

### Known limitations

- MTP is Windows-only. On Linux the picker returns empty.
- The bundled `.exe` is ~80 MB (PyInstaller + Flet runtime).
- Unsigned binary: Windows SmartScreen may prompt the user on first
  launch.

---

[Unreleased]: https://github.com/Juanpablo9717/switch-queue-copy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Juanpablo9717/switch-queue-copy/releases/tag/v0.1.0
