"""Human-readable formatting helpers (no I/O, no UI)."""

from __future__ import annotations


def fmt_size(n: float) -> str:
    """Format a byte count as 'X.YZ MB' / 'X.YZ GB' / etc."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


def fmt_eta(seconds: float) -> str:
    """Format remaining seconds as '12s' / '4m 23s' / '2h 14m'."""
    if seconds <= 0 or seconds == float("inf"):
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
