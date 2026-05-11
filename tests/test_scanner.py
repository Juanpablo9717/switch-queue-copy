"""Scanner: discovers games (one rule, handles single/library/collection)."""

from __future__ import annotations

from pathlib import Path

from switch_queue.core import scan_source

from .conftest import touch


class TestScanSource:
    def test_single_game_folder_returns_one_game(self, tmp_path: Path):
        touch(tmp_path, "Big Helmet Heroes [010044B01E786000][v0].nsp")
        touch(tmp_path, "Big Helmet Heroes [010044B01E786800][v131072].nsp")

        games = scan_source(tmp_path)

        assert len(games) == 1
        assert len(games[0].files) == 2
        cats = sorted(f.category for f in games[0].files)
        assert cats == ["base", "update"]
        assert games[0].source_root == tmp_path.resolve()

    def test_library_returns_one_game_per_subfolder(self, tmp_path: Path):
        touch(tmp_path, "GameA/A [0100AAAAAAAA0000][v0].nsp")
        touch(tmp_path, "GameA/A [0100AAAAAAAA0800][v0].nsp")
        touch(tmp_path, "GameB/B [0100BBBBBBBB0000][v0].nsz")

        games = scan_source(tmp_path)

        assert len(games) == 2
        names = sorted(g.name for g in games)
        assert names == ["GameA", "GameB"]

    def test_collection_treats_each_subgame_as_separate(self, tmp_path: Path):
        # Like Trine Collection / SteamWorld Collection
        touch(tmp_path, "Coll/Trine 2/Trine 2 [0100CCC000000000][v0].nsz")
        touch(tmp_path, "Coll/Trine 2/Trine 2 [0100CCC000000800][v0].nsz")
        touch(tmp_path, "Coll/Trine 3/Trine 3 [0100DDD000000000][v0].nsz")

        games = scan_source(tmp_path)

        assert len(games) == 2
        names = sorted(g.name for g in games)
        assert any("Trine 2" in n for n in names)
        assert any("Trine 3" in n for n in names)

    def test_dlc_subfolder_files_attach_to_parent_game(self, tmp_path: Path):
        touch(tmp_path, "Dungeons/Dungeons [0100EEE000000000][v0].nsz")
        touch(tmp_path, "Dungeons/Dungeons [0100EEE000000800][v0].nsz")
        touch(tmp_path, "Dungeons/7 DLC/DLC1 [0100EEE000000001][v0].nsp")
        touch(tmp_path, "Dungeons/7 DLC/DLC2 [0100EEE000000002][v0].nsp")

        games = scan_source(tmp_path)

        assert len(games) == 1
        cats = sorted(f.category for f in games[0].files)
        assert cats == ["base", "dlc", "dlc", "update"]

    def test_translation_folder_with_atmosphere_is_skipped_even_with_nsps(self, tmp_path: Path):
        """A folder whose NAME doesn't contain 'mod' but ships an
        atmosphere/contents/ subdir + patched .nsp files is still a mod.
        Real example: Pokemon Scarlet/Violet 'Russian Machine Translation
        (24.05.2025)' which holds re-packaged updates with a translation
        patch baked in. We must not surface those as separate games.
        """
        # Two real Pokemon games at top level
        touch(tmp_path, "Bundle/Pokemon Scarlet/Pokemon Scarlet [0100A3D008C5C000][v0].nsp")
        touch(tmp_path, "Bundle/Pokemon Scarlet/Pokemon Scarlet [0100A3D008C5C800][v786432].nsp")
        touch(tmp_path, "Bundle/Pokemon Violet/Pokemon Violet [01008F6008C5E000][v0].nsp")
        touch(tmp_path, "Bundle/Pokemon Violet/Pokemon Violet [01008F6008C5E800][v786432].nsp")

        # The translation pack: harmless name, but contains atmosphere mods
        # AND patched .nsp files at its root
        touch(tmp_path, "Bundle/Russian Translation (24.05.2025)/Pokemon Scarlet [0100A3D008C5C800][v720896].nsp")
        touch(tmp_path, "Bundle/Russian Translation (24.05.2025)/Pokemon Violet [01008F6008C5E800][v720896].nsp")
        touch(tmp_path, "Bundle/Russian Translation (24.05.2025)/atmosphere/contents/0100A3D008C5C000/romfs/main.bin", content=b"x")
        touch(tmp_path, "Bundle/Russian Translation (24.05.2025)/ReadMe_Rus.txt", content=b"hi")

        games = scan_source(tmp_path)

        # Exactly TWO games: Scarlet and Violet — the translation folder is filtered out.
        assert len(games) == 2
        names = sorted(g.name for g in games)
        assert any("Pokemon Scarlet" in n for n in names)
        assert any("Pokemon Violet" in n for n in names)

        # And neither game has a stray v720896 update sneaked in from the mod folder.
        for g in games:
            for f in g.files:
                assert "720896" not in f.rel.name, (
                    f"Translation-mod NSP leaked into queue: {f.rel}"
                )

    def test_mod_subfolders_are_skipped(self, tmp_path: Path):
        touch(tmp_path, "Game/Game [0100FFF000000000][v0].nsz")
        touch(
            tmp_path,
            "Game/Russian Voice Mod/atmosphere/contents/0100FFF000000000/romfs/audio.fbq",
            content=b"x",
        )
        touch(
            tmp_path,
            "Game/TagNX exeFS Mod/atmosphere/contents/0100FFF000000000/exefs/main.npdm",
            content=b"x",
        )
        # An NSP misplaced inside a Mod folder MUST NOT appear
        touch(tmp_path, "Game/TagNX exeFS Mod/Game [0100FFF000000800][v9109504].nsp")

        games = scan_source(tmp_path)

        assert len(games) == 1
        assert len(games[0].files) == 1
        assert games[0].files[0].category == "base"

    def test_empty_folder_returns_empty(self, tmp_path: Path):
        assert scan_source(tmp_path) == []

    def test_folder_with_only_unrelated_files_is_empty(self, tmp_path: Path):
        touch(tmp_path, "readme.txt", content=b"hi")
        touch(tmp_path, "notes.md", content=b"hi")
        assert scan_source(tmp_path) == []

    def test_flat_bundle_splits_by_title_id(self, tmp_path: Path):
        """A flat folder mixing multiple distinct Title IDs (e.g. ACA NEOGEO
        Metal Slug 1,2,3,4,5-X) splits into one Game entry per game family.
        All entries share the same destination folder.
        """
        # ML1: base + update         (TID prefix 0100EBE002B3)
        touch(tmp_path, "Bundle/ACA SLUG [0100EBE002B3E000][v0].nsp")
        touch(tmp_path, "Bundle/ACA SLUG [0100EBE002B3E800][v131072].nsp")
        # ML2: base only             (TID prefix 010086300486)
        touch(tmp_path, "Bundle/ACA SLUG 2 [010086300486E000][v0].nsp")
        # ML3: base + update         (TID prefix 0100BA8001DC)
        touch(tmp_path, "Bundle/ACA SLUG 3 [0100BA8001DC6000][v0].nsp")
        touch(tmp_path, "Bundle/ACA SLUG 3 [0100BA8001DC6800][v131072].nsp")

        games = scan_source(tmp_path)

        # Three distinct Title-ID prefixes → three separate Game entries
        assert len(games) == 3

        # All map to the same physical destination folder
        for g in games:
            assert g.rel == Path("Bundle")

        by_name = {g.name: g for g in games}

        # Names derived from filenames (longest common prefix)
        assert "ACA SLUG" in by_name
        assert "ACA SLUG 2" in by_name
        assert "ACA SLUG 3" in by_name

        # File counts and categories per group
        assert len(by_name["ACA SLUG"].files) == 2
        assert sorted(f.category for f in by_name["ACA SLUG"].files) == ["base", "update"]

        assert len(by_name["ACA SLUG 2"].files) == 1
        assert by_name["ACA SLUG 2"].files[0].category == "base"

        assert len(by_name["ACA SLUG 3"].files) == 2
        assert sorted(f.category for f in by_name["ACA SLUG 3"].files) == ["base", "update"]

    def test_single_title_id_folder_does_not_split(self, tmp_path: Path):
        """A folder with base + update + multiple DLCs (all same Title-ID
        family) stays as ONE game — no false split.
        """
        # All share TID prefix 0100EEE00000
        touch(tmp_path, "Game/Game [0100EEE000000000][v0].nsz")
        touch(tmp_path, "Game/Game [0100EEE000000800][v131072].nsz")
        # DLCs differ at position 12 but share positions 0..11
        touch(tmp_path, "Game/DLC/Game [DLC A] [0100EEE000001001][v0].nsp")
        touch(tmp_path, "Game/DLC/Game [DLC B] [0100EEE000001002][v0].nsp")

        games = scan_source(tmp_path)

        assert len(games) == 1
        assert len(games[0].files) == 4
        cats = sorted(f.category for f in games[0].files)
        assert cats == ["base", "dlc", "dlc", "update"]

    def test_files_without_title_id_dont_fragment(self, tmp_path: Path):
        """Files without parseable Title IDs share one fallback bucket and
        produce a single Game entry (no per-file split).
        """
        touch(tmp_path, "Folder/random_a.nsp")
        touch(tmp_path, "Folder/random_b.nsp")

        games = scan_source(tmp_path)

        assert len(games) == 1
        assert len(games[0].files) == 2
