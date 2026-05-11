"""
Classification of Switch game files into BASE / UPDATE / DLC.

The rule, in order of priority:
    1. If the path includes a folder matching DLC_FOLDER_RE  → 'dlc'
    2. If the filename has '[DLC ...]'                        → 'dlc'
    3. Title ID (16 hex chars in []) ending in:
         '000' → 'base'
         '800' → 'update'
         else  → 'dlc'
    4. Fallback                                                → 'base'
"""

from __future__ import annotations

import re
from pathlib import Path

# Recognized game-file extensions
GAME_EXTS = {".nsp", ".nsz", ".xci"}

# Title ID is a 16-hex-char string in square brackets, e.g. [0100D71004694000]
TITLE_ID_RE = re.compile(r"\[([0-9a-fA-F]{16})\]")

# Folders to ignore entirely (mods)
MOD_FOLDER_RE = re.compile(r"\bmod\b|atmosphere", re.IGNORECASE)

# DLC subfolder names: 'DLC', '7 DLC', '12 DLC', '38 DLC'
DLC_FOLDER_RE = re.compile(r"^\s*(\d+\s*)?DLC\b", re.IGNORECASE)

# DLC hint embedded in filename: '[DLC Pack Name]'
DLC_NAME_HINT_RE = re.compile(r"\[DLC\b", re.IGNORECASE)


def classify_file(rel: Path, filename: str) -> str:
    """Return 'base', 'update', or 'dlc' for a Switch game file."""
    # 1) Folder hint
    for p in rel.parts[:-1]:
        if DLC_FOLDER_RE.search(p):
            return "dlc"
    # 2) Filename hint
    if DLC_NAME_HINT_RE.search(filename):
        return "dlc"
    # 3) Title ID
    m = TITLE_ID_RE.search(filename)
    if m:
        suffix = m.group(1).lower()[-3:]
        if suffix == "000":
            return "base"
        if suffix == "800":
            return "update"
        return "dlc"
    # 4) Fallback
    return "base"
