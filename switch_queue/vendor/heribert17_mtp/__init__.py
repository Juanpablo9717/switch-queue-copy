"""
Vendored subset of Heribert17/mtp (MIT licensed).
Source: https://github.com/Heribert17/mtp
Vendored at commit: HEAD on 2026-05-05.

Only `win_access.py` is included (Windows MTP/WPD access). The Linux
backend, libmtp wrapper, and tkinter dialog were intentionally not
vendored — we ship our own Flet-native picker.

Why vendor instead of `pip install`:
    The upstream `setup.py` expects a `src/` layout that doesn't exist
    in the repository, so `pip install git+...` fails. Vendoring also
    makes our PyInstaller build reproducible.
"""
