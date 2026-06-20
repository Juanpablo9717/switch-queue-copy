"""
Platform-dispatched MTP provider used by the picker UI.

Windows  -> WPD/COM backend (``mtp.py``); the chosen destination is an
            ``mtp://`` URI handled by :class:`MtpBackend`.
Linux    -> gvfs backend (``mtp_linux.py``); the chosen destination is a
            plain filesystem path under the gvfs mount, handled by
            :class:`LocalBackend`.

The picker imports ``list_devices`` / ``list_device_folders`` /
``build_destination`` from here and stays platform-agnostic. ``mtp.py``
remains 100% Windows-only and no new dependency is added — the Linux path
shells out to ``gio``.
"""

from __future__ import annotations

import sys


if sys.platform == "win32":
    from .mtp import MtpBackend, build_uri, list_device_folders, list_devices

    class MtpUnavailable(RuntimeError):
        """Never raised on Windows; present so the picker can catch it."""

    def build_destination(device, parts: list[str]) -> str:
        device_name = device.name or device.devicename
        return build_uri(device_name, *parts)

    def make_mtp_backend(dest_uri: str):
        return MtpBackend(dest_uri)

else:
    from .mtp_linux import (  # noqa: F401
        LinuxMtpBackend,
        MtpUnavailable,
        build_destination,
        list_device_folders,
        list_devices,
    )

    def make_mtp_backend(dest_uri: str):
        return LinuxMtpBackend(dest_uri)


__all__ = [
    "list_devices",
    "list_device_folders",
    "build_destination",
    "make_mtp_backend",
    "MtpUnavailable",
]
