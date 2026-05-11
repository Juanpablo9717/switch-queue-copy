"""
MTP / WPD destination backend (Windows only).

Wraps the vendored Heribert17 WPD bindings so the copier doesn't have to
know anything about COM, devices, or storages.

How we get **fine-grained progress + mid-file pause/skip/cancel** despite
the underlying ``upload_file`` API not exposing callbacks:

    Heribert17's ``_upload_stream`` calls ``inputstream.read(blocksize)``
    in a loop, then ``filestream.Commit(0)`` once empty. We pass our own
    ``_ProgressStream`` that:
      * counts bytes read and forwards to ``on_progress``;
      * honors pause/cancel/skip via the shared CopyState;
      * raises a private exception to abort cleanly mid-upload.

    The COM filestream is then never committed (we deliberately bail
    before ``Commit``), and we delete any partial object on the device
    via ``remove()`` to avoid orphan stubs.

URI format used in app state and the destination text field:

    mtp://<friendly device name>/<storage name>/<sub>/<path>

Examples:

    mtp://Switch/MicroSD/Install
    mtp://Galaxy S20/Internal storage/DCIM/Camera

The *friendly* name (``device.name``) is used for readability. If multiple
devices match by name, the first one wins. Storage and folder names match
case-sensitively (MTP convention).
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Callable, Iterator

from ..models import CopyState
from .base import RESULT_CANCEL, RESULT_ERROR, RESULT_OK, RESULT_SKIP


URI_PREFIX = "mtp://"


def is_mtp_uri(s: str) -> bool:
    return s.lower().startswith(URI_PREFIX)


# ---------------------------------------------------------------------------
# Lazy-import the vendored Heribert17 bindings.
#
# `comtypes` initialization can be slow and is Windows-only. Importing on
# demand keeps the rest of the app (tests, Linux dev) decoupled.
# ---------------------------------------------------------------------------

_win_access = None  # populated on first call
_import_error: str | None = None


def _wa():
    """Return the Heribert17 win_access module, importing on first use."""
    global _win_access, _import_error
    if _win_access is not None:
        return _win_access
    if sys.platform != "win32":
        raise RuntimeError("MTP backend is Windows-only.")
    try:
        from ...vendor.heribert17_mtp import win_access
        _win_access = win_access
        return _win_access
    except Exception as e:
        _import_error = str(e)
        raise


def list_devices(force_refresh: bool = True) -> list:
    """Enumerate connected MTP devices.

    WPD's ``IPortableDeviceManager`` caches its device list internally —
    Heribert17 keeps the manager in a module global and reuses it, so a
    device plugged in *after* the first ``GetDevices`` call won't appear
    on subsequent calls. ``RefreshDeviceList`` is the official way to
    force a re-scan; if it isn't exposed for some reason we fall back to
    discarding the cached manager so the next call rebuilds it.
    """
    wa = _wa()
    if force_refresh and wa.DEVICE_MANAGER is not None:
        try:
            wa.DEVICE_MANAGER.RefreshDeviceList()
        except Exception:
            wa.DEVICE_MANAGER = None
    return wa.get_portable_devices()


# ---------------------------------------------------------------------------
# URI parsing
# ---------------------------------------------------------------------------


def parse_uri(uri: str) -> tuple[str, list[str]]:
    """Split ``mtp://<device>/<storage>/<path>`` into (device_name, [parts]).

    The returned list always starts with the storage name.
    """
    if not is_mtp_uri(uri):
        raise ValueError(f"Not an MTP URI: {uri!r}")
    rest = uri[len(URI_PREFIX):]
    parts = [p for p in rest.replace("\\", "/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(
            f"MTP URI needs at least device + storage: {uri!r}"
        )
    return parts[0], parts[1:]


def build_uri(device_name: str, *path_parts: str) -> str:
    """Reverse of parse_uri — construct a ``mtp://...`` URI."""
    cleaned = [p for p in path_parts if p]
    return URI_PREFIX + "/".join([device_name, *cleaned])


def _resolve_device(name: str):
    """Find a connected device whose ``.name`` matches `name` (first wins)."""
    devices = list_devices()
    for dev in devices:
        if dev.name == name:
            return dev
    # Relaxed fallback: match against the composite devicename.
    for dev in devices:
        if dev.devicename == name or name in dev.devicename:
            return dev
    raise IOError(f"MTP device not found: {name!r}")


def _device_path(device, parts: list[str]) -> str:
    """Build the OS-sep-joined path Heribert17 expects:
    ``<devicename>\\<storage>\\<sub>\\...``.
    """
    return os.sep.join([device.devicename, *parts])


# ---------------------------------------------------------------------------
# Progress / control stream wrapper
# ---------------------------------------------------------------------------


class _UploadCancelled(Exception):
    """Internal — raised from the read-side wrapper to abort an upload."""


class _UploadSkipped(Exception):
    """Internal — raised on user 'skip current file' during MTP upload."""


class _ProgressStream:
    """File-like wrapper that exposes read() with progress + control hooks.

    Heribert17's ``_upload_stream`` only calls ``.read(n)`` in a loop, so
    duck-typing a minimal subset is enough.
    """

    def __init__(self, fp, on_progress: Callable[[int], None], state: CopyState) -> None:
        self._fp = fp
        self._on_progress = on_progress
        self._state = state
        self._read_total = 0

    def read(self, n: int = -1) -> bytes:
        # Honor control events between blocks.
        if self._state.cancel_event.is_set():
            raise _UploadCancelled
        while self._state.pause_event.is_set():
            if self._state.cancel_event.is_set():
                raise _UploadCancelled
            import time
            time.sleep(0.1)
        if self._state.skip_event.is_set():
            self._state.skip_event.clear()
            raise _UploadSkipped

        block = self._fp.read(n)
        if block:
            self._read_total += len(block)
            self._on_progress(self._read_total)
        return block

    # Minimal io.FileIO surface that Heribert17 might touch.
    def close(self) -> None:
        pass

    @property
    def closed(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# MtpBackend
# ---------------------------------------------------------------------------


class MtpBackend:
    """Writes to a folder on a connected MTP device.

    Construct from a URI; the device handle is resolved eagerly so the
    user gets a clear error before the queue starts copying.

    Why we don't use Heribert17's ``makedirs`` / ``get_content_from_device_path``:
    those helpers internally call ``os.path.join``. On Windows, joining
    ``"DeviceName"`` with a storage like ``"5: SD Card install"`` causes
    Python to interpret ``5:`` as a drive letter and **discard** the first
    arg — leaving a 1-component path that the library then refuses with
    *"needs a devicename and a storage as paramter"*. That breaks every
    DBI-style storage name (DBI numbers them ``"1:"``, ``"2:"``, ...).

    We bypass entirely by walking the device tree ourselves with explicit
    parent + child navigation — no path strings, no ``os.path.join``.
    """

    def __init__(self, dest_uri: str) -> None:
        device_name, parts = parse_uri(dest_uri)
        self._device = _resolve_device(device_name)
        # `parts` is [storage, sub, sub, ...]
        self._base_parts: list[str] = parts
        self.uri = dest_uri

    # -- traversal helpers (no path strings, no os.path.join) --------------

    def _resolve_storage(self, storage_name: str):
        """Find the storage on the device whose ``.name`` matches."""
        for s in self._device.get_content():
            if s.name == storage_name:
                return s
        raise IOError(f"Storage not found on device: {storage_name!r}")

    def _walk_to(self, parts: list[str], create_missing: bool = False):
        """Resolve ``[storage, sub, sub, ...]`` to a PortableDeviceContent.

        Returns ``None`` when a segment doesn't exist and ``create_missing``
        is False. Creates folders on the way down when True. Never builds a
        path string — we use ``get_child`` / ``create_content`` step by step.
        """
        if not parts:
            return None
        storage = self._resolve_storage(parts[0])
        current = storage
        for sub in parts[1:]:
            child = current.get_child(sub)
            if child is None:
                if not create_missing:
                    return None
                child = current.create_content(sub)
            current = child
        return current

    def _abs_parts(self, rel_path: Path, *extra: str) -> list[str]:
        rel_parts = [p for p in rel_path.parts if p not in ("", ".")]
        return [*self._base_parts, *rel_parts, *extra]

    # -- DestinationBackend ------------------------------------------------

    def make_dirs(self, rel_path: Path):
        return self._walk_to(self._abs_parts(rel_path), create_missing=True)

    def file_exists_with_size(self, rel_path: Path, filename: str, expected: int) -> bool:
        try:
            content = self._walk_to(self._abs_parts(rel_path, filename))
        except IOError:
            return False
        if content is None:
            return False
        return getattr(content, "size", -1) == expected

    def remove_partial(self, rel_path: Path, filename: str) -> None:
        try:
            content = self._walk_to(self._abs_parts(rel_path, filename))
            if content is not None:
                content.remove()
        except Exception:
            pass

    def upload(
        self,
        src: Path,
        rel_path: Path,
        filename: str,
        size: int,
        state: CopyState,
        on_progress: Callable[[int], None],
    ) -> str:
        try:
            dest_folder = self._walk_to(self._abs_parts(rel_path), create_missing=True)
            if dest_folder is None:
                return RESULT_ERROR
        except Exception:
            return RESULT_ERROR

        # Defensive: if a stub of the same name already exists, drop it so
        # we get a clean upload.
        try:
            existing = dest_folder.get_child(filename)
            if existing is not None:
                existing.remove()
        except Exception:
            pass

        try:
            with io.FileIO(str(src), "rb") as raw:
                stream = _ProgressStream(raw, on_progress, state)
                # Bypass `upload_file` (which re-opens) and feed our wrapper
                # straight into the streaming routine.
                dest_folder._upload_stream(filename, stream, size)
            on_progress(size)  # final beat
            return RESULT_OK
        except _UploadCancelled:
            self.remove_partial(rel_path, filename)
            return RESULT_CANCEL
        except _UploadSkipped:
            self.remove_partial(rel_path, filename)
            return RESULT_SKIP
        except Exception:
            self.remove_partial(rel_path, filename)
            return RESULT_ERROR


# ---------------------------------------------------------------------------
# Friendly device/folder enumeration helpers (used by the picker UI)
# ---------------------------------------------------------------------------


def list_device_folders(device, parts: list[str]) -> Iterator:
    """Yield child PortableDeviceContent objects under ``parts`` on `device`.

    `parts` is the path on the device starting at the storage; an empty
    list yields the storages.
    """
    if not parts:
        for storage in device.get_content():
            yield storage
        return

    full = _device_path(device, parts)
    content = _wa().get_content_from_device_path(device, full)
    if content is None:
        return
    for child in content.get_children():
        yield child
