"""Domain logic: scanning, classification, models, backends, and the copier."""

from .backends import (
    COPY_BUF,
    DestinationBackend,
    LocalBackend,
    MtpBackend,
    build_uri,
    is_mtp_uri,
    parse_uri,
)
from .classifier import (
    DLC_FOLDER_RE,
    DLC_NAME_HINT_RE,
    GAME_EXTS,
    MOD_FOLDER_RE,
    TITLE_ID_RE,
    classify_file,
)
from .copier import SPEED_WINDOW, make_backend, run_copy_queue
from .models import (
    LOG_DEBUG,
    LOG_ERROR,
    LOG_INFO,
    LOG_WARN,
    CopyEvent,
    CopyState,
    Game,
    GameFile,
    LogEntry,
)
from .scanner import scan_source

__all__ = [
    # classifier
    "GAME_EXTS",
    "TITLE_ID_RE",
    "MOD_FOLDER_RE",
    "DLC_FOLDER_RE",
    "DLC_NAME_HINT_RE",
    "classify_file",
    # models
    "Game",
    "GameFile",
    "CopyEvent",
    "CopyState",
    "LogEntry",
    "LOG_DEBUG",
    "LOG_INFO",
    "LOG_WARN",
    "LOG_ERROR",
    # scanner
    "scan_source",
    # copier + backends
    "COPY_BUF",
    "SPEED_WINDOW",
    "make_backend",
    "run_copy_queue",
    "DestinationBackend",
    "LocalBackend",
    "MtpBackend",
    "is_mtp_uri",
    "parse_uri",
    "build_uri",
]
