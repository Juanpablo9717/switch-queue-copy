"""
Destination backend protocol.

Each backend implements the same surface so the copier doesn't care whether
it's writing to a local filesystem path or to an MTP/WPD device.

Methods are intentionally tiny and synchronous — pause/skip/cancel are
honored *inside* the upload via the shared CopyState.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from ..models import CopyState


# Result strings returned by `upload`. Identical for every backend.
RESULT_OK = "done"
RESULT_CANCEL = "cancel"
RESULT_SKIP = "skip"
RESULT_ERROR = "error"


@runtime_checkable
class DestinationBackend(Protocol):
    """Where a queue copies its files to."""

    def make_dirs(self, rel_path: Path) -> None:
        """Ensure the destination subtree at `rel_path` exists."""

    def file_exists_with_size(self, rel_path: Path, filename: str, expected: int) -> bool:
        """True iff a same-size file already lives at the destination."""

    def remove_partial(self, rel_path: Path, filename: str) -> None:
        """Best-effort cleanup of an interrupted upload."""

    def upload(
        self,
        src: Path,
        rel_path: Path,
        filename: str,
        size: int,
        state: CopyState,
        on_progress: Callable[[int], None],
    ) -> str:
        """Send `src` to <dest_root>/<rel_path>/<filename>.

        `on_progress(bytes_done)` is called periodically (best-effort).
        Honors `state.pause_event`, `state.skip_event`, `state.cancel_event`.
        Returns one of RESULT_OK, RESULT_CANCEL, RESULT_SKIP, RESULT_ERROR.
        """
