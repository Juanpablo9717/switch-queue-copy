"""
Linux MTP destination support via gvfs (``gio``).

Unlike Windows — where MTP needs the WPD/COM stack (see ``mtp.py``) — on
Linux an MTP device mounted by **gvfs** shows up as an ordinary directory
under ``/run/user/<uid>/gvfs/mtp:host=.../``. Reading and writing it are
plain filesystem operations, so the existing :class:`LocalBackend` copies
to it unchanged (strict-serial, progress, pause/skip/cancel all for free).

This module therefore implements **no copy backend**. It only:

  * discovers connected MTP devices (gvfs volumes),
  * mounts any the desktop hasn't mounted yet (``gio mount``),
  * exposes each mount as a folder tree the picker can browse.

The picker then hands the copier a **plain filesystem path** (not an
``mtp://`` URI), which ``make_backend`` routes to ``LocalBackend``.

Requirements: the ``gio`` CLI (ships with GLib/GVFS) plus the gvfs MTP
backend — package ``gvfs-mtp`` on Arch/Fedora, ``gvfs-backends`` on
Debian/Ubuntu. When ``gio`` is missing we raise :class:`MtpUnavailable`
with an actionable message; the picker turns that into a localized hint.

Why shell out to ``gio`` instead of binding libmtp directly: it adds no
new Python dependency (keeping the Windows build untouched), it cooperates
with the desktop's own mount instead of fighting it for the USB device,
and it works the same on every GVFS-based desktop.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import unquote

from ..models import CopyState
from .base import RESULT_CANCEL, RESULT_ERROR, RESULT_OK, RESULT_SKIP
from .mtp import build_uri, parse_uri


# Mirror the Heribert17/Windows content_type convention the picker filters
# on: 0 = STORAGE, 1 = DIRECTORY, 2 = FILE. We only emit DIRECTORY/FILE;
# storages on Linux are just the first level of folders inside the mount.
_DIR = 1
_FILE = 2

_MTP_MOUNT_GLOB = "mtp:host=*"
_MTP_MOUNT_PREFIX = "mtp:host="
_MTP_URI_PREFIX = "mtp://"


class MtpUnavailable(RuntimeError):
    """``gio`` / the gvfs MTP backend is not available on this system."""


@dataclass
class LinuxMtpDevice:
    """A gvfs-mounted MTP device, presented to the picker like a Windows one."""

    name: str          # friendly label, e.g. "DBI"
    devicename: str    # mount dir name, e.g. "mtp:host=-_DBI_XTJ50380016740"
    mount_path: Path   # /run/user/<uid>/gvfs/mtp:host=...


@dataclass
class LinuxMtpEntry:
    """A child of a device folder. Shares the attribute surface the picker
    reads from Windows content objects (``name``, ``_plain_name``,
    ``content_type``)."""

    name: str
    _plain_name: str
    content_type: int


# ---------------------------------------------------------------------------
# gio / gvfs plumbing
# ---------------------------------------------------------------------------


def _gio() -> str:
    gio = shutil.which("gio")
    if gio is None:
        raise MtpUnavailable("gio not found")
    return gio


def _gvfs_dir() -> Path:
    return Path(f"/run/user/{os.getuid()}/gvfs")


def _existing_mounts() -> list[Path]:
    """gvfs MTP mounts currently present on the filesystem (source of truth)."""
    d = _gvfs_dir()
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob(_MTP_MOUNT_GLOB) if p.is_dir())


def _host_of(s: str) -> str:
    """Normalize a mount dir name or an activation_root to its host token.

    ``mtp:host=-_DBI_XTJ50380016740``  -> ``-_DBI_XTJ50380016740``
    ``mtp://-_DBI_XTJ50380016740/``    -> ``-_DBI_XTJ50380016740``
    URL-encoded forms are decoded so the two representations compare equal.
    """
    if s.startswith(_MTP_MOUNT_PREFIX):
        s = s[len(_MTP_MOUNT_PREFIX):]
    elif s.startswith(_MTP_URI_PREFIX):
        s = s[len(_MTP_URI_PREFIX):].rstrip("/")
    return unquote(s)


def _list_mtp_volumes() -> list[tuple[str, str]]:
    """Parse ``gio mount -li`` into ``[(label, activation_root)]`` for MTP.

    Returns ``[]`` (rather than raising) on any gio error so discovery can
    still fall back to mounts already present on disk.
    """
    try:
        proc = subprocess.run(
            [_gio(), "mount", "-li"],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    vols: list[tuple[str, str]] = []
    label = ""
    is_mtp = False
    root = ""

    def flush() -> None:
        nonlocal label, is_mtp, root
        if is_mtp and root:
            vols.append((label or _host_of(root), root))
        label, is_mtp, root = "", False, ""

    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if line.startswith("Volume("):
            flush()
            # 'Volume(0): DBI'
            _, _, lab = line.partition(":")
            label = lab.strip()
        elif "GProxyVolumeMonitorMTP" in line:
            is_mtp = True
        elif line.startswith("activation_root="):
            root = line[len("activation_root="):].strip()
    flush()
    return vols


def _mount(activation_root: str) -> None:
    """Best-effort ``gio mount``. Errors (e.g. device busy) are swallowed —
    the caller re-scans the filesystem to learn what actually mounted."""
    try:
        subprocess.run(
            [_gio(), "mount", activation_root],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        pass


def _friendly(host: str) -> str:
    """Best-effort device label from a host token: '-_DBI_XTJ...' -> 'DBI'."""
    parts = [p for p in host.split("_") if p and p != "-"]
    return parts[0] if parts else host


# ---------------------------------------------------------------------------
# Public surface (matches mtp.py so the picker stays platform-agnostic)
# ---------------------------------------------------------------------------


def list_devices(force_refresh: bool = True) -> list[LinuxMtpDevice]:
    """Discover MTP devices, mounting any gvfs sees but hasn't mounted yet.

    Raises :class:`MtpUnavailable` when ``gio`` is absent.
    """
    _gio()  # raises MtpUnavailable if missing

    vols = _list_mtp_volumes()
    mounted_hosts = {_host_of(p.name) for p in _existing_mounts()}
    for _label, root in vols:
        if _host_of(root) not in mounted_hosts:
            _mount(root)

    label_by_host = {_host_of(root): label for label, root in vols}
    devices: list[LinuxMtpDevice] = []
    for mp in _existing_mounts():
        host = _host_of(mp.name)
        name = label_by_host.get(host) or _friendly(host)
        devices.append(
            LinuxMtpDevice(name=name, devicename=mp.name, mount_path=mp)
        )
    return devices


def list_device_folders(
    device: LinuxMtpDevice, parts: list[str]
) -> Iterator[LinuxMtpEntry]:
    """Yield children under ``parts`` of ``device``. ``parts == []`` lists
    the storages (the first level of folders inside the mount)."""
    base = device.mount_path
    for p in parts:
        base = base / p
    try:
        entries = list(os.scandir(base))
    except OSError:
        return
    for e in entries:
        try:
            is_dir = e.is_dir()
        except OSError:
            is_dir = False
        yield LinuxMtpEntry(
            name=e.name,
            _plain_name=e.name,
            content_type=_DIR if is_dir else _FILE,
        )


def build_destination(device: LinuxMtpDevice, parts: list[str]) -> str:
    """An ``mtp://<host>/<storage>/<parts>`` URI for the chosen folder.

    ``make_backend`` routes this to :class:`LinuxMtpBackend`, which copies
    with ``gio copy`` (required for DBI install storages — see below). The
    host token is gvfs's, so it round-trips to the mount path.
    """
    return build_uri(_host_of(device.devicename), *parts)


# ---------------------------------------------------------------------------
# LinuxMtpBackend — copies via `gio copy`
# ---------------------------------------------------------------------------
#
# Why not just write to the gvfs mount path with open()/shutil (i.e. reuse
# LocalBackend)? Because that works for ordinary storages but FAILS on DBI's
# "install" storages: gvfs creates a zero-byte object first and streams into
# it, and DBI rejects that — the object can't even be created (Errno 5).
#
# `gio copy` instead hands libmtp the file *with its size up front*
# (LIBMTP_Send_File_From_File), which is exactly what the Windows WPD path
# does and what DBI's MTP responder expects. That makes install storages
# work, and it copies to ordinary storages too — so it's the one upload
# mechanism for every Linux MTP destination.
#
# Fine-grained control maps onto the child process: progress comes from
# parsing ``gio copy -p`` (under ``LC_ALL=C`` so the text is stable),
# pause = SIGSTOP/SIGCONT, cancel/skip = terminate.


# Matches e.g. "Copied 5.5 MB out of 20.0 MB (...)" under LC_ALL=C.
_PROGRESS_RE = re.compile(r"Copied\s+([\d.]+)\s*(bytes|[KkMGT]?B)\s+out of")
_UNIT = {
    "bytes": 1, "B": 1,
    "kB": 1000, "KB": 1000,
    "MB": 1000**2, "GB": 1000**3, "TB": 1000**4,
}


def _parse_progress_bytes(line: str) -> int | None:
    m = _PROGRESS_RE.search(line)
    if not m:
        return None
    try:
        return int(float(m.group(1)) * _UNIT.get(m.group(2), 1))
    except ValueError:
        return None


def _is_install_storage(name: str) -> bool:
    """DBI's drop-zone storages ("5: SD Card install", "6: NAND install")
    install on receipt and reject sub-folders — files must arrive flat."""
    return "install" in name.lower()


def _stop_process(proc: subprocess.Popen) -> None:
    """Resume-if-paused, then terminate, then hard-kill as a last resort."""
    for sig in (signal.SIGCONT, signal.SIGTERM):
        try:
            proc.send_signal(sig)
        except Exception:
            pass
    try:
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class LinuxMtpBackend:
    """Writes to an MTP device on Linux via ``gio copy``.

    Construct from an ``mtp://<host>/<storage>/<sub>`` URI (as produced by
    :func:`build_destination`). Mirrors the Windows :class:`MtpBackend`
    surface so the copier is platform-agnostic.
    """

    def __init__(self, dest_uri: str) -> None:
        host, parts = parse_uri(dest_uri)
        self.uri = dest_uri
        self._host = host
        self._base_parts = parts  # [storage, sub, ...]
        self._mount_path = _gvfs_dir() / f"{_MTP_MOUNT_PREFIX}{host}"
        self._is_install = bool(parts) and _is_install_storage(parts[0])

    # -- path helpers ------------------------------------------------------

    def _target_dir_parts(self, rel_path: Path) -> list[str]:
        # DBI install storages take files flat; ordinary storages mirror the
        # source folder structure.
        if self._is_install:
            return list(self._base_parts)
        rel = [p for p in Path(rel_path).parts if p not in ("", ".")]
        return [*self._base_parts, *rel]

    def _mount_dir(self, rel_path: Path) -> Path:
        p = self._mount_path
        for part in self._target_dir_parts(rel_path):
            p = p / part
        return p

    def _target_file_uri(self, rel_path: Path, filename: str) -> str:
        return build_uri(self._host, *self._target_dir_parts(rel_path), filename)

    def _target_dir_uri(self, rel_path: Path) -> str:
        # gio copy must address the *directory* (SendObject into it), not an
        # explicit filename — DBI's install drop-zone rejects being addressed
        # by name. gio then names the object from the source's basename
        # (which equals `filename` for every real queue entry).
        return build_uri(self._host, *self._target_dir_parts(rel_path)) + "/"

    # -- DestinationBackend ------------------------------------------------

    def make_dirs(self, rel_path: Path) -> None:
        if self._is_install:
            return  # flat drop-zone; no sub-folders
        try:
            self._mount_dir(rel_path).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def file_exists_with_size(self, rel_path: Path, filename: str, expected: int) -> bool:
        # Install storages consume the file on receipt, so nothing persists
        # to compare against — always (re)send.
        if self._is_install:
            return False
        p = self._mount_dir(rel_path) / filename
        try:
            return p.exists() and p.stat().st_size == expected
        except OSError:
            return False

    def remove_partial(self, rel_path: Path, filename: str) -> None:
        try:
            subprocess.run(
                [_gio(), "remove", self._target_file_uri(rel_path, filename)],
                capture_output=True, timeout=15,
            )
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
        target = self._target_dir_uri(rel_path)
        env = dict(os.environ)
        env["LC_ALL"] = "C"  # stable, parseable progress text
        env["LANG"] = "C"

        try:
            proc = subprocess.Popen(
                [_gio(), "copy", "-p", str(src), target],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
        except (OSError, subprocess.SubprocessError):
            return RESULT_ERROR

        # gio writes progress with carriage returns; universal-newline text
        # mode splits on them, so each update arrives as its own "line".
        progress = {"bytes": 0}

        def _reader() -> None:
            try:
                for line in proc.stdout:  # type: ignore[union-attr]
                    b = _parse_progress_bytes(line)
                    if b is not None:
                        progress["bytes"] = b
            except Exception:
                pass

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        paused = False
        result: str | None = None
        try:
            while proc.poll() is None:
                if state.cancel_event.is_set():
                    _stop_process(proc)
                    result = RESULT_CANCEL
                    break
                if state.skip_event.is_set():
                    state.skip_event.clear()
                    _stop_process(proc)
                    result = RESULT_SKIP
                    break
                if state.pause_event.is_set() and not paused:
                    try:
                        proc.send_signal(signal.SIGSTOP)
                        paused = True
                    except Exception:
                        pass
                elif not state.pause_event.is_set() and paused:
                    try:
                        proc.send_signal(signal.SIGCONT)
                        paused = False
                    except Exception:
                        pass
                on_progress(progress["bytes"])
                time.sleep(0.1)
        finally:
            if paused:
                try:
                    proc.send_signal(signal.SIGCONT)
                except Exception:
                    pass
            reader.join(timeout=1)

        if result in (RESULT_CANCEL, RESULT_SKIP):
            self.remove_partial(rel_path, filename)
            return result
        if proc.returncode == 0:
            on_progress(size)  # final beat
            return RESULT_OK
        self.remove_partial(rel_path, filename)
        return RESULT_ERROR
