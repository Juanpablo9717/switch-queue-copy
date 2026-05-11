"""
Robust system-clipboard read/write.

Why not tkinter:
    Tk's ``clipboard_append`` / ``clipboard_get`` rely on Tk **owning a
    window** while the data is on the clipboard. On Windows, destroying
    the Tk root releases ownership and the OS may discard the bytes
    before another app has a chance to paste. We saw exactly that: the
    snackbar said "copied" but Ctrl+V pasted whatever was on the
    clipboard before.

Why not Flet's ``page.clipboard.set``:
    In Flet 0.84 it's a **coroutine** — calling it from a sync
    handler returns the coroutine object without ever awaiting it
    (RuntimeWarning: coroutine was never awaited). Silent no-op.

What this module does:
    On Windows we go straight to user32/kernel32 via ctypes — the same
    APIs Notepad uses. ``SetClipboardData`` transfers a global memory
    handle to the OS, which then owns the data — no window dependency.

    On non-Windows we fall back to tkinter (less reliable but enough
    for dev work / Linux smoke tests).

Both ``set_text`` and ``get_text`` are sync and return on completion.
``get_text`` exists mainly for the round-trip test in
``tests/test_clipboard.py``.
"""

from __future__ import annotations

import sys

# ---------------------------------------------------------------------------
# Windows backend
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wt

    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    # Explicit signatures so 64-bit handles aren't truncated to int.
    _user32.OpenClipboard.argtypes = [wt.HWND]
    _user32.OpenClipboard.restype = wt.BOOL
    _user32.CloseClipboard.argtypes = []
    _user32.CloseClipboard.restype = wt.BOOL
    _user32.EmptyClipboard.argtypes = []
    _user32.EmptyClipboard.restype = wt.BOOL
    _user32.SetClipboardData.argtypes = [wt.UINT, wt.HANDLE]
    _user32.SetClipboardData.restype = wt.HANDLE
    _user32.GetClipboardData.argtypes = [wt.UINT]
    _user32.GetClipboardData.restype = wt.HANDLE

    _kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
    _kernel32.GlobalAlloc.restype = wt.HGLOBAL
    _kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
    _kernel32.GlobalLock.restype = wt.LPVOID
    _kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]
    _kernel32.GlobalUnlock.restype = wt.BOOL
    _kernel32.GlobalFree.argtypes = [wt.HGLOBAL]
    _kernel32.GlobalFree.restype = wt.HGLOBAL

    def set_text(text: str) -> bool:
        """Place `text` on the system clipboard. Returns True on success."""
        if text is None:
            text = ""
        # UTF-16 LE with NUL terminator — what CF_UNICODETEXT expects.
        encoded = (text + "\0").encode("utf-16-le")
        n_bytes = len(encoded)

        if not _user32.OpenClipboard(None):
            return False
        try:
            _user32.EmptyClipboard()
            handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, n_bytes)
            if not handle:
                return False
            ptr = _kernel32.GlobalLock(handle)
            if not ptr:
                _kernel32.GlobalFree(handle)
                return False
            ctypes.memmove(ptr, encoded, n_bytes)
            _kernel32.GlobalUnlock(handle)
            if not _user32.SetClipboardData(CF_UNICODETEXT, handle):
                # Ownership wasn't transferred; we still own the handle.
                _kernel32.GlobalFree(handle)
                return False
            return True
        finally:
            _user32.CloseClipboard()

    def get_text() -> str | None:
        """Return current clipboard text (or None if unavailable / not text)."""
        if not _user32.OpenClipboard(None):
            return None
        try:
            handle = _user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return None
            ptr = _kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                return ctypes.wstring_at(ptr)
            finally:
                _kernel32.GlobalUnlock(handle)
        finally:
            _user32.CloseClipboard()

# ---------------------------------------------------------------------------
# Non-Windows fallback (tkinter, less robust but does the job for tests)
# ---------------------------------------------------------------------------

else:
    def set_text(text: str) -> bool:  # type: ignore[no-redef]
        try:
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            return True
        except Exception:
            return False

    def get_text() -> str | None:  # type: ignore[no-redef]
        try:
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            value = root.clipboard_get()
            root.destroy()
            return value
        except Exception:
            return None
