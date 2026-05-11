"""
Design tokens with light/dark variants.

The current theme lives in module-level `current`. Components read from it
lazily (`theme.current.surface`), so when the App calls `set_mode(...)` and
rebuilds the UI, every component picks up the new colors.

Default is dark.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """All color tokens used across the UI for a given mode."""

    name: str          # "light" | "dark"

    # Surfaces / chrome
    bg: str            # outermost page bg
    surface: str       # cards
    surface_2: str     # nested / inset bgs (source-card body, etc.)
    border: str        # hairline border on cards & rows

    # Text
    text: str
    text_muted: str

    # Brand / interactive
    primary: str       # buttons, focused borders, brand icon
    primary_bg: str    # filled badge bg (e.g. "31 juegos")
    primary_fg: str    # filled badge fg

    # Status
    danger: str
    progress_bg: str

    # Snackbars
    snack_ok_bg: str
    snack_ok_fg: str
    snack_err_bg: str
    snack_err_fg: str

    # BASE / UPDATE / DLC tag chip styles
    tag_styles: dict


# ---------------------------------------------------------------------------
# Light theme — improved contrast over the previous all-white look
# ---------------------------------------------------------------------------

LIGHT = Theme(
    name="light",
    bg="#eef2f7",            # slate-100-ish, distinct from white cards
    surface="#ffffff",
    surface_2="#f1f5f9",
    border="#cbd5e1",        # slate-300, clearly visible
    text="#0f172a",
    text_muted="#64748b",
    primary="#2563eb",
    primary_bg="#dbeafe",
    primary_fg="#1e40af",
    danger="#dc2626",
    progress_bg="#e2e8f0",
    snack_ok_bg="#dcfce7",
    snack_ok_fg="#166534",
    snack_err_bg="#fee2e2",
    snack_err_fg="#991b1b",
    tag_styles={
        "base":   {"bg": "#dbeafe", "fg": "#1e40af", "label": "BASE"},
        "update": {"bg": "#fef3c7", "fg": "#92400e", "label": "UPDATE"},
        "dlc":    {"bg": "#ede9fe", "fg": "#6d28d9", "label": "DLC"},
    },
)


# ---------------------------------------------------------------------------
# Dark theme — slate-based, low-glare, default
# ---------------------------------------------------------------------------

DARK = Theme(
    name="dark",
    bg="#0b1220",            # slightly deeper than slate-900
    surface="#111a2e",        # cards
    surface_2="#0b1220",      # nested rows recede to bg color
    border="#27324a",         # subtle but visible against surface
    text="#e2e8f0",
    text_muted="#94a3b8",
    primary="#60a5fa",        # blue-400, brighter for dark
    primary_bg="#1e3a8a",
    primary_fg="#bfdbfe",
    danger="#f87171",
    progress_bg="#1e293b",
    snack_ok_bg="#14532d",
    snack_ok_fg="#bbf7d0",
    snack_err_bg="#7f1d1d",
    snack_err_fg="#fecaca",
    tag_styles={
        "base":   {"bg": "#1e3a8a", "fg": "#bfdbfe", "label": "BASE"},
        "update": {"bg": "#78350f", "fg": "#fde68a", "label": "UPDATE"},
        "dlc":    {"bg": "#4c1d95", "fg": "#ddd6fe", "label": "DLC"},
    },
)


# ---------------------------------------------------------------------------
# Current theme (mutable, swap with set_mode)
# ---------------------------------------------------------------------------

current: Theme = DARK


def set_mode(mode: str) -> None:
    """Switch the active theme. `mode` is 'light' or 'dark'."""
    global current
    current = DARK if mode == "dark" else LIGHT


# ---------------------------------------------------------------------------
# Window sizing (theme-independent)
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 820
WINDOW_MIN_WIDTH = 980
WINDOW_MIN_HEIGHT = 640
