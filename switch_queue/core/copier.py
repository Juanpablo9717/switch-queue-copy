"""
Copy worker: serial queue copier with pause/skip/cancel and live progress.

Single thread, single ``for`` loop — that's what guarantees no two files
are ever in flight (see ``tests/test_copier.py``). The actual byte
transfer is delegated to a ``DestinationBackend`` (local FS or MTP).

The copier emits ``CopyEvent``s through a callback; the UI subscribes.
"""

from __future__ import annotations

import collections
import time
from pathlib import Path
from typing import Callable

from .backends import (
    COPY_BUF,
    DestinationBackend,
    LocalBackend,
    RESULT_CANCEL,
    RESULT_ERROR,
    RESULT_OK,
    RESULT_SKIP,
    is_mtp_uri,
)
from .backends.mtp_provider import make_mtp_backend
from .models import CopyEvent, CopyState, Game, GameFile

# Moving-average window for speed/ETA in seconds.
SPEED_WINDOW = 3.0

__all__ = [
    "COPY_BUF",
    "SPEED_WINDOW",
    "make_backend",
    "run_copy_queue",
]


CopyCallback = Callable[[CopyEvent], None]


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------


def make_backend(destination: str | Path) -> DestinationBackend:
    """Pick a backend based on the destination string/path.

    A ``mtp://...`` URI gives the platform's MTP backend (WPD on Windows,
    ``gio copy`` on Linux); anything else is treated as a local filesystem
    path.
    """
    s = str(destination)
    if is_mtp_uri(s):
        return make_mtp_backend(s)
    return LocalBackend(Path(s))


def run_copy_queue(
    queue: list[tuple[Game, GameFile]],
    destination: str | Path | DestinationBackend,
    overwrite: bool,
    state: CopyState,
    on_event: CopyCallback,
) -> None:
    """
    Sequentially copy each (Game, GameFile) using the chosen backend.

    Designed to run in a worker thread. Keep the implementation a plain
    ``for`` loop — that's what makes the queue strictly serial.
    """
    if isinstance(destination, DestinationBackend):
        backend = destination
    else:
        backend = make_backend(destination)

    total_bytes = sum(gf.size for _, gf in queue)
    bytes_done = 0
    recent: collections.deque = collections.deque()  # (timestamp, total_done)

    # Outcome counters surfaced in the final queue_done event so the UI
    # can tell the difference between "completed cleanly" and "completed
    # with N errors".
    ok_count = 0
    error_count = 0
    skip_count = 0

    _emit(on_event, "queue_start", total_files=len(queue), total_bytes=total_bytes)

    for idx, (game, gf) in enumerate(queue):
        if state.cancel_event.is_set():
            _emit(
                on_event, "queue_done",
                result="cancelled", total_bytes=total_bytes,
                ok_count=ok_count, error_count=error_count, skip_count=skip_count,
            )
            return

        # Preserve the source_root name in the destination so two different
        # sources with the same game name don't collide.
        rel_dest = Path(game.source_root.name) / game.rel
        try:
            backend.make_dirs(rel_dest)
        except Exception as e:
            _emit(on_event, "error", message=f"No puedo crear carpeta: {e}")
            error_count += 1
            # Surface as a per-item error so the UI status & log catch it.
            _emit(on_event, "item_done", result="error", file=gf)
            continue

        _emit(on_event, "item_start", idx=idx, total=len(queue), game=game, file=gf)

        # Skip if destination already has a same-size file (resumable).
        if not overwrite and backend.file_exists_with_size(rel_dest, gf.rel.name, gf.size):
            _emit(on_event, "item_done", result="skip-existing", file=gf)
            skip_count += 1
            bytes_done += gf.size
            _emit(
                on_event,
                "item_progress",
                file_done=gf.size,
                file_total=gf.size,
                total_done=bytes_done,
                total_bytes=total_bytes,
                speed=0,
                eta=0,
            )
            continue

        # Per-item progress callback wraps timing + speed/ETA in a closure.
        last_ui = [0.0]

        def on_progress(file_done: int, _idx=idx, _gf=gf, _bytes_done_before=bytes_done):
            now = time.monotonic()
            if now - last_ui[0] <= 0.1:
                return
            last_ui[0] = now
            total_done = _bytes_done_before + file_done
            recent.append((now, total_done))
            while recent and now - recent[0][0] > SPEED_WINDOW:
                recent.popleft()
            speed = 0.0
            eta = 0.0
            if len(recent) >= 2:
                dt = recent[-1][0] - recent[0][0]
                db = recent[-1][1] - recent[0][1]
                if dt > 0:
                    speed = db / dt
                    if speed > 0:
                        eta = (total_bytes - total_done) / speed
            _emit(
                on_event,
                "item_progress",
                file_done=file_done,
                file_total=_gf.size,
                total_done=total_done,
                total_bytes=total_bytes,
                speed=speed,
                eta=eta,
            )

        result = backend.upload(
            src=gf.src,
            rel_path=rel_dest,
            filename=gf.rel.name,
            size=gf.size,
            state=state,
            on_progress=on_progress,
        )

        if result == RESULT_CANCEL:
            backend.remove_partial(rel_dest, gf.rel.name)
            _emit(
                on_event, "queue_done",
                result="cancelled", total_bytes=total_bytes,
                ok_count=ok_count, error_count=error_count, skip_count=skip_count,
            )
            return
        if result == RESULT_SKIP:
            backend.remove_partial(rel_dest, gf.rel.name)
            _emit(on_event, "item_done", result="skip-manual", file=gf)
            skip_count += 1
            bytes_done += gf.size
            continue
        if result == RESULT_ERROR:
            backend.remove_partial(rel_dest, gf.rel.name)
            _emit(on_event, "item_done", result="error", file=gf)
            error_count += 1
            bytes_done += gf.size
            continue

        # OK — final progress beat with totals.
        ok_count += 1
        bytes_done += gf.size
        _emit(
            on_event,
            "item_progress",
            file_done=gf.size,
            file_total=gf.size,
            total_done=bytes_done,
            total_bytes=total_bytes,
            speed=0.0,
            eta=0.0,
        )
        _emit(on_event, "item_done", result="ok", file=gf)

    _emit(
        on_event, "queue_done",
        result="completed", total_bytes=total_bytes,
        ok_count=ok_count, error_count=error_count, skip_count=skip_count,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _emit(cb: CopyCallback, kind: str, **payload) -> None:
    cb(CopyEvent(kind=kind, payload=payload))
