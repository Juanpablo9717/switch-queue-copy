"""
Local-filesystem destination backend.

This is the historical behaviour of the app: copy files via Python's
``open()`` + ``shutil``, with a 4 MB buffer. Pause/skip/cancel are
checked between buffer reads, giving fine-grained mid-file control.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Callable

from ..models import CopyState
from .base import RESULT_CANCEL, RESULT_ERROR, RESULT_OK, RESULT_SKIP

# 4 MB sweet spot: ~95% of disk speed and snappy control-event polling.
COPY_BUF = 4 * 1024 * 1024


class LocalBackend:
    """Writes to a folder on the host filesystem (Path)."""

    def __init__(self, dst_root: Path) -> None:
        self.dst_root = dst_root

    # -- DestinationBackend ------------------------------------------------

    def make_dirs(self, rel_path: Path) -> None:
        (self.dst_root / rel_path).mkdir(parents=True, exist_ok=True)

    def file_exists_with_size(self, rel_path: Path, filename: str, expected: int) -> bool:
        p = self.dst_root / rel_path / filename
        try:
            return p.exists() and p.stat().st_size == expected
        except OSError:
            return False

    def remove_partial(self, rel_path: Path, filename: str) -> None:
        try:
            (self.dst_root / rel_path / filename).unlink()
        except OSError:
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
        dst = self.dst_root / rel_path / filename
        try:
            with open(src, "rb") as fs, open(dst, "wb") as fd:
                copied = 0
                while True:
                    if state.cancel_event.is_set():
                        return RESULT_CANCEL
                    while state.pause_event.is_set():
                        if state.cancel_event.is_set():
                            return RESULT_CANCEL
                        time.sleep(0.1)
                    if state.skip_event.is_set():
                        state.skip_event.clear()
                        return RESULT_SKIP

                    buf = fs.read(COPY_BUF)
                    if not buf:
                        break
                    fd.write(buf)
                    copied += len(buf)
                    on_progress(copied)

            try:
                shutil.copystat(src, dst)
            except OSError:
                pass
            on_progress(size)  # final beat
            return RESULT_OK
        except Exception:
            return RESULT_ERROR
