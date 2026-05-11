"""Pluggable destination backends — local filesystem and MTP/WPD."""

from .base import (
    RESULT_CANCEL,
    RESULT_ERROR,
    RESULT_OK,
    RESULT_SKIP,
    DestinationBackend,
)
from .local import COPY_BUF, LocalBackend
from .mtp import MtpBackend, build_uri, is_mtp_uri, parse_uri

__all__ = [
    "DestinationBackend",
    "LocalBackend",
    "MtpBackend",
    "COPY_BUF",
    "RESULT_OK",
    "RESULT_CANCEL",
    "RESULT_SKIP",
    "RESULT_ERROR",
    "is_mtp_uri",
    "parse_uri",
    "build_uri",
]
