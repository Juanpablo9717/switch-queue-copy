"""
End-to-end clipboard test.

Writes a sentinel string with our helper, then reads it back. The reader
uses the **same** ctypes path on Windows but the test still proves the
write+read works against the real OS clipboard, not just our internal
state.

Skipped on non-Windows because the tkinter fallback requires a working
display server, which isn't guaranteed in CI containers — and Windows
is the only platform we ship the .exe for anyway.
"""

from __future__ import annotations

import sys

import pytest

from switch_queue.utils import clipboard


@pytest.mark.skipif(sys.platform != "win32", reason="Windows clipboard only")
class TestClipboardRoundTrip:
    SENTINEL = "switch_queue clipboard round-trip · 0123 ñü 🟢"

    def test_set_returns_true_on_success(self):
        assert clipboard.set_text(self.SENTINEL) is True

    def test_get_text_after_set_returns_same_string(self):
        ok = clipboard.set_text(self.SENTINEL)
        assert ok, "set_text returned False"
        got = clipboard.get_text()
        assert got == self.SENTINEL, (
            f"clipboard round-trip mismatch.\n"
            f"  expected: {self.SENTINEL!r}\n"
            f"  got     : {got!r}"
        )

    def test_set_overwrites_previous_contents(self):
        clipboard.set_text("first value")
        assert clipboard.get_text() == "first value"
        clipboard.set_text("second value")
        assert clipboard.get_text() == "second value"

    def test_set_handles_long_multiline_text(self):
        # Mimic a real log dump (~50 lines, ~5 KB of text).
        lines = [f"[12:34:{i:02d}] INFO  Line {i} of the dump" for i in range(50)]
        big = "\n".join(lines)
        assert clipboard.set_text(big) is True
        got = clipboard.get_text()
        assert got == big

    def test_set_handles_empty_string(self):
        assert clipboard.set_text("") is True
        assert clipboard.get_text() == ""
