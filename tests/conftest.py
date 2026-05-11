"""Shared pytest helpers and fixtures."""

from __future__ import annotations

from pathlib import Path

from switch_queue.core import CopyEvent, Game, GameFile


def touch(root: Path, rel: str, *, content: bytes = b"") -> Path:
    """Create a file under `root` with optional content. Makes parent dirs."""
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p


def collect_events(events: list[CopyEvent], kind: str) -> list[CopyEvent]:
    return [e for e in events if e.kind == kind]


def make_queue(
    tmp_path: Path,
    n_files: int,
    file_size_kb: int = 8,
) -> tuple[list[tuple[Game, GameFile]], Path]:
    """Build a queue of `n_files` synthetic files for copy testing."""
    src_root = tmp_path / "src"
    dst_root = tmp_path / "dst"
    src_root.mkdir()
    dst_root.mkdir()

    queue: list[tuple[Game, GameFile]] = []
    for i in range(n_files):
        cat = ["base", "update", "dlc"][i % 3]
        suffix = {"base": "0000", "update": "0800", "dlc": "0001"}[cat]
        fname = f"f{i:02d}_[0100{i:08X}{suffix}][v0].nsp"
        path = touch(src_root, fname, content=b"X" * (file_size_kb * 1024))
        gf = GameFile(src=path, rel=Path(fname), size=path.stat().st_size, category=cat)
        g = Game(name=f"Game{i}", src=src_root, rel=Path("."), source_root=src_root, files=[gf])
        queue.append((g, gf))
    return queue, dst_root
