"""
Copier tests — including the CRITICAL serial invariant.

The user's #1 concern: never two files copying at once. These tests prove
that, regardless of file size or speed, the queue runs strictly one item
at a time and in the order given.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from switch_queue.core import (
    CopyEvent,
    CopyState,
    run_copy_queue,
)
from switch_queue.core import copier as copier_module

from .conftest import collect_events, make_queue


class TestCopySerialInvariant:
    def test_run_completes_with_correct_event_sequence(self, tmp_path: Path):
        queue, dst_root = make_queue(tmp_path, n_files=5)
        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=False, state=CopyState(), on_event=events.append)

        assert len(collect_events(events, "queue_start")) == 1
        done = collect_events(events, "queue_done")
        assert len(done) == 1
        assert done[0].payload["result"] == "completed"
        assert len(collect_events(events, "item_start")) == 5
        assert len(collect_events(events, "item_done")) == 5

    def test_no_two_files_in_flight_at_once(self, tmp_path: Path):
        """At no point should two files be 'in flight' simultaneously."""
        queue, dst_root = make_queue(tmp_path, n_files=8)
        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=False, state=CopyState(), on_event=events.append)

        in_flight: set[int] = set()
        max_concurrent = 0
        idx_by_file = {id(gf): i for i, (_, gf) in enumerate(queue)}

        for e in events:
            if e.kind == "item_start":
                in_flight.add(e.payload["idx"])
            elif e.kind == "item_done":
                idx = idx_by_file[id(e.payload["file"])]
                in_flight.discard(idx)
            max_concurrent = max(max_concurrent, len(in_flight))

        assert max_concurrent <= 1, (
            f"Two or more files were in flight at the same time (max={max_concurrent}). "
            "Serial invariant broken."
        )

    def test_each_item_done_precedes_next_item_start(self, tmp_path: Path):
        queue, dst_root = make_queue(tmp_path, n_files=6)
        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=False, state=CopyState(), on_event=events.append)

        starts_pos = [i for i, e in enumerate(events) if e.kind == "item_start"]
        dones_pos = [i for i, e in enumerate(events) if e.kind == "item_done"]

        assert len(starts_pos) == len(dones_pos) == len(queue)
        for k in range(len(queue) - 1):
            assert dones_pos[k] < starts_pos[k + 1]

    def test_files_copy_in_queue_order(self, tmp_path: Path):
        queue, dst_root = make_queue(tmp_path, n_files=10)
        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=False, state=CopyState(), on_event=events.append)

        starts = collect_events(events, "item_start")
        for i, ev in enumerate(starts):
            assert ev.payload["idx"] == i
            assert ev.payload["file"] is queue[i][1]

    def test_destination_files_match_sources(self, tmp_path: Path):
        queue, dst_root = make_queue(tmp_path, n_files=4)
        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=False, state=CopyState(), on_event=events.append)

        for game, gf in queue:
            dst = dst_root / game.source_root.name / game.rel / gf.rel
            assert dst.exists()
            assert dst.stat().st_size == gf.size


class TestQueueControl:
    """Pause / Skip / Cancel during an in-progress queue."""

    @pytest.fixture
    def slow_copy(self, monkeypatch):
        """Shrink the copy buffer so each file takes longer."""
        monkeypatch.setattr(copier_module, "COPY_BUF", 1024)
        yield

    def test_cancel_stops_queue_promptly(self, tmp_path: Path, slow_copy):
        queue, dst_root = make_queue(tmp_path, n_files=20, file_size_kb=512)
        state = CopyState()
        events: list[CopyEvent] = []
        lock = threading.Lock()

        def on_event(e: CopyEvent) -> None:
            with lock:
                events.append(e)
            if e.kind == "item_start" and e.payload["idx"] == 1:
                state.cancel_event.set()

        worker = threading.Thread(
            target=run_copy_queue,
            args=(queue, dst_root, False, state, on_event),
        )
        worker.start()
        worker.join(timeout=20)

        assert not worker.is_alive(), "Worker did not exit after cancel"
        with lock:
            done = collect_events(events, "queue_done")
            starts = collect_events(events, "item_start")
        assert len(done) == 1
        assert done[0].payload["result"] == "cancelled"
        assert len(starts) < 20

    def test_skip_marks_current_file_as_skipped_and_continues(self, tmp_path: Path, slow_copy):
        queue, dst_root = make_queue(tmp_path, n_files=4, file_size_kb=512)
        state = CopyState()
        events: list[CopyEvent] = []
        lock = threading.Lock()
        skipped_idx = 1

        def on_event(e: CopyEvent) -> None:
            with lock:
                events.append(e)
            if e.kind == "item_start" and e.payload["idx"] == skipped_idx:
                state.skip_event.set()

        worker = threading.Thread(
            target=run_copy_queue,
            args=(queue, dst_root, False, state, on_event),
        )
        worker.start()
        worker.join(timeout=20)

        assert not worker.is_alive()
        with lock:
            dones = collect_events(events, "item_done")
        assert len(dones) == 4
        assert dones[skipped_idx].payload["result"] == "skip-manual"
        g, gf = queue[skipped_idx]
        dst = dst_root / g.source_root.name / g.rel / gf.rel
        assert not dst.exists()
        for i, e in enumerate(dones):
            if i != skipped_idx:
                assert e.payload["result"] == "ok"

    def test_pause_blocks_progress_until_cleared(self, tmp_path: Path, slow_copy):
        queue, dst_root = make_queue(tmp_path, n_files=4, file_size_kb=512)
        state = CopyState()
        events: list[CopyEvent] = []
        lock = threading.Lock()

        state.pause_event.set()  # pause BEFORE start

        def on_event(e: CopyEvent) -> None:
            with lock:
                events.append(e)

        worker = threading.Thread(
            target=run_copy_queue,
            args=(queue, dst_root, False, state, on_event),
        )
        worker.start()
        time.sleep(0.5)

        with lock:
            done_before = len(collect_events(events, "item_done"))
        assert done_before == 0, "Queue completed items while paused"

        state.pause_event.clear()
        worker.join(timeout=20)
        assert not worker.is_alive()

        with lock:
            dones = collect_events(events, "item_done")
            qdone = collect_events(events, "queue_done")
        assert len(dones) == 4
        assert qdone[0].payload["result"] == "completed"
