"""
Scanner: walk a folder and detect Switch game folders.

A "game folder" is any folder that has at least one .nsp/.nsz/.xci directly
inside it. The same rule handles:
    - Single game (the chosen folder IS a game folder → 1 result)
    - Library  (the chosen folder contains many game folders → N results)
    - Collection (e.g. Trine Collection → each subfolder is a game)

It also handles **flat multi-game bundles** (e.g. ACA NEOGEO Metal Slug
1,2,3,4,5-X — six distinct games crammed into one flat folder): when a
single folder produces files belonging to multiple distinct Title IDs, it
is split into one Game entry per Title-ID family. All split entries share
the same physical destination, so files end up in the original folder
structure on disk.

Mods are skipped: any folder whose name contains 'mod' or 'atmosphere' is
not descended into.
"""

from __future__ import annotations

import os
from pathlib import Path

from .classifier import GAME_EXTS, MOD_FOLDER_RE, TITLE_ID_RE, classify_file
from .models import Game, GameFile


def scan_source(source: Path) -> list[Game]:
    """Walk `source` and return detected Games (alphabetically sorted)."""
    games: list[Game] = []
    source = source.resolve()

    for dirpath, dirnames, filenames in os.walk(source):
        d = Path(dirpath)
        rel_dir = Path(".") if d == source else d.relative_to(source)

        # Skip everything inside a mod subtree
        if any(MOD_FOLDER_RE.search(p) for p in rel_dir.parts if p != "."):
            dirnames.clear()
            continue

        # Game folder = has direct game files
        direct = [f for f in filenames if Path(f).suffix.lower() in GAME_EXTS]
        if not direct:
            continue

        # Structural mod check: any folder that contains an
        # ``atmosphere/contents/`` subdir is a Switch homebrew mod (Russian
        # translations, patched updates, etc.). The .nsp files at its root
        # are patched copies that the user almost certainly does not want
        # to install over their library — skip the whole subtree.
        if _looks_like_mod(d):
            dirnames.clear()
            continue

        # Collect all game files at this level and below (excluding mod paths)
        game_files: list[GameFile] = []
        for sub_dp, sub_dn, sub_fn in os.walk(d):
            sd = Path(sub_dp)
            rel_from_game = Path(".") if sd == d else sd.relative_to(d)
            if any(MOD_FOLDER_RE.search(p) for p in rel_from_game.parts if p != "."):
                sub_dn.clear()
                continue
            for f in sub_fn:
                if Path(f).suffix.lower() not in GAME_EXTS:
                    continue
                full = sd / f
                rel = full.relative_to(d)
                try:
                    size = full.stat().st_size
                except OSError:
                    continue
                game_files.append(
                    GameFile(src=full, rel=rel, size=size, category=classify_file(rel, f))
                )

        if not game_files:
            continue

        folder_name = str(rel_dir) if rel_dir != Path(".") else d.name
        groups = _group_by_title_id(game_files)

        if len(groups) <= 1:
            # Single-game folder — keep historical behavior, name = folder name.
            games.append(
                Game(name=folder_name, src=d, rel=rel_dir, source_root=source, files=game_files)
            )
        else:
            # Flat multi-game bundle — one Game per Title-ID family. All split
            # entries share `src`/`rel`, so they map to the same destination.
            for tid_prefix, group_files in groups.items():
                derived = _derive_game_name(group_files)
                display_name = derived or f"{folder_name} ({tid_prefix})"
                games.append(
                    Game(
                        name=display_name,
                        src=d,
                        rel=rel_dir,
                        source_root=source,
                        files=group_files,
                    )
                )

        # Don't descend further: avoids treating nested DLC subfolders as games.
        dirnames.clear()

    games.sort(key=lambda g: g.name.lower())
    return games


# ---------------------------------------------------------------------------
# Mod detection by structure
# ---------------------------------------------------------------------------


def _looks_like_mod(folder: Path) -> bool:
    """True if `folder` has an ``atmosphere/contents/`` subdir.

    The Atmosphère homebrew CFW uses ``atmosphere/contents/<TitleID>/...``
    to deliver romfs/exefs patches. Any folder shipping this structure is
    a mod regardless of what it's named on disk — including translations,
    patched updates, fan retextures, etc.
    """
    try:
        return (folder / "atmosphere" / "contents").is_dir()
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Title-ID grouping for flat multi-game bundles
# ---------------------------------------------------------------------------


def _title_id_prefix(filename: str) -> str | None:
    """First 12 hex chars of the Title ID in `filename`, or None.

    Switch Title IDs are 16 hex chars. Positions 0..11 identify the *game
    family* (base + updates + DLCs share these). Positions 12..15 vary
    between BASE / UPDATE / DLC of the same game. Grouping by the first 12
    keeps a game's base + update + DLCs together while separating unrelated
    games like the six Metal Slugs in an ACA NEOGEO bundle.
    """
    m = TITLE_ID_RE.search(filename)
    if not m:
        return None
    return m.group(1).lower()[:12]


def _group_by_title_id(files: list[GameFile]) -> dict[str, list[GameFile]]:
    """Group `files` by Title-ID prefix.

    Files without a parseable Title ID land in a single fallback bucket so
    they stay together (no fragmentation into N "unknown" games).
    Insertion order is preserved (Python 3.7+ dict).
    """
    groups: dict[str, list[GameFile]] = {}
    for gf in files:
        key = _title_id_prefix(gf.rel.name) or "__no_tid__"
        groups.setdefault(key, []).append(gf)
    return groups


def _derive_game_name(files: list[GameFile]) -> str:
    """Longest common prefix of filenames before the first '[', cleaned up.

    Switch dumps follow a `<Game Name> [<TitleID>][...].ext` convention, so
    splitting on the first '[' isolates the human-readable name. Across the
    files of a single Title-ID family this is normally identical (e.g. all
    "ACA NEOGEO METAL SLUG 3" entries), so the common-prefix folding is a
    safety net for inconsistent dumps.
    """
    parts = [f.rel.name.split("[", 1)[0].rstrip() for f in files]
    if not parts:
        return ""
    common = parts[0]
    for n in parts[1:]:
        i = 0
        while i < len(common) and i < len(n) and common[i] == n[i]:
            i += 1
        common = common[:i]
    return common.rstrip(" -._")
