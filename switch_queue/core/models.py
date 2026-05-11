"""
Domain dataclasses shared across scanner, classifier, and copier.

No I/O, no UI. Pure data containers.
"""

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Game / file model
# ---------------------------------------------------------------------------


@dataclass
class GameFile:
    """A single .nsp/.nsz/.xci that belongs to a Game."""
    src: Path           # absolute source path
    rel: Path           # path relative to its game folder
    size: int           # bytes
    category: str       # 'base' | 'update' | 'dlc'
    selected: bool = True


@dataclass
class Game:
    """A game folder grouping its base / updates / DLC files."""
    name: str           # display name (typically rel-from-source-root)
    src: Path           # absolute path of the game folder
    rel: Path           # path relative to source_root
    source_root: Path   # the user-provided root the game was scanned from
    files: list[GameFile] = field(default_factory=list)
    selected: bool = True

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def selected_size(self) -> int:
        return sum(f.size for f in self.files if f.selected)


# ---------------------------------------------------------------------------
# Copy worker control & events
# ---------------------------------------------------------------------------


@dataclass
class CopyState:
    """Three threading.Events the worker checks while copying."""
    pause_event: threading.Event = field(default_factory=threading.Event)
    skip_event: threading.Event = field(default_factory=threading.Event)
    cancel_event: threading.Event = field(default_factory=threading.Event)


# ---------------------------------------------------------------------------
# Log entries (for the in-app Logs panel)
# ---------------------------------------------------------------------------


# String constants instead of an Enum to keep payloads JSON-friendly and the
# dataclass trivially serializable.
LOG_DEBUG = "debug"
LOG_INFO = "info"
LOG_WARN = "warn"
LOG_ERROR = "error"


@dataclass
class LogEntry:
    """One line in the in-app log drawer."""
    timestamp: datetime.datetime
    level: str          # one of LOG_DEBUG / LOG_INFO / LOG_WARN / LOG_ERROR
    message: str


@dataclass
class CopyEvent:
    """
    Event emitted by the copy worker.

    The kind drives the payload contract:
        'queue_start'   -> total_files, total_bytes
        'item_start'    -> idx, total, game, file
        'item_progress' -> file_done, file_total, total_done, total_bytes, speed, eta
        'item_done'     -> result ('ok'|'skip-existing'|'skip-manual'|'error'), file
        'queue_done'    -> result ('completed'|'cancelled'), total_bytes
        'error'         -> message
    """
    kind: str
    payload: dict
