"""Skip-existing and overwrite behaviour."""

from __future__ import annotations

from pathlib import Path

from switch_queue.core import CopyEvent, CopyState, run_copy_queue

from .conftest import collect_events, make_queue


class TestSkipExisting:
    def test_skips_when_dest_exists_with_same_size_and_overwrite_false(self, tmp_path: Path):
        queue, dst_root = make_queue(tmp_path, n_files=2)
        # Pre-create dest of first file with matching size, different content.
        g, gf = queue[0]
        dst = dst_root / g.source_root.name / g.rel / gf.rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"Y" * gf.size)

        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=False, state=CopyState(), on_event=events.append)

        dones = collect_events(events, "item_done")
        assert dones[0].payload["result"] == "skip-existing"
        assert dones[1].payload["result"] == "ok"
        # Pre-existing content preserved (Y, not X)
        assert dst.read_bytes()[:10] == b"YYYYYYYYYY"

    def test_overwrites_when_overwrite_true(self, tmp_path: Path):
        queue, dst_root = make_queue(tmp_path, n_files=1)
        g, gf = queue[0]
        dst = dst_root / g.source_root.name / g.rel / gf.rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"Y" * gf.size)

        events: list[CopyEvent] = []
        run_copy_queue(queue, dst_root, overwrite=True, state=CopyState(), on_event=events.append)

        # File now contains X (from source)
        assert dst.read_bytes()[:10] == b"XXXXXXXXXX"
        assert collect_events(events, "item_done")[0].payload["result"] == "ok"
