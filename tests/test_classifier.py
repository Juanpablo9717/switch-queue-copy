"""Classification rules: BASE / UPDATE / DLC / fallback."""

from __future__ import annotations

from pathlib import Path

from switch_queue.core import classify_file


class TestClassifyFile:
    """The 16-hex Title ID's last 3 chars + folder/name hints decide category."""

    def test_base_when_title_id_ends_in_000(self):
        assert classify_file(
            Path("Game [0100D71004694000][v0].nsp"),
            "Game [0100D71004694000][v0].nsp",
        ) == "base"

    def test_update_when_title_id_ends_in_800(self):
        assert classify_file(
            Path("Game [0100D71004694800][v9699328].nsp"),
            "Game [0100D71004694800][v9699328].nsp",
        ) == "update"

    def test_dlc_when_title_id_ends_in_other(self):
        fn = "Minecraft Nintendo Switch Edition [DLC 1st Birthday Skin Pack] [01006BD001E07021][v0].nsp"
        assert classify_file(Path(fn), fn) == "dlc"

    def test_dlc_when_inside_dlc_folder(self):
        rel = Path("7 DLC") / "FakeName [0100ABC000000000][v0].nsp"
        assert classify_file(rel, rel.name) == "dlc"

    def test_dlc_when_filename_has_dlc_tag(self):
        fn = "Some Game [DLC Pack] [0100AAA111222333][v0].nsp"
        assert classify_file(Path(fn), fn) == "dlc"

    def test_dlc_when_inside_numbered_dlc_folder(self):
        rel = Path("12 DLC") / "Anything.nsp"
        assert classify_file(rel, rel.name) == "dlc"

    def test_no_title_id_falls_back_to_base(self):
        assert classify_file(Path("randomfile.nsp"), "randomfile.nsp") == "base"

    def test_case_insensitive_dlc_tag(self):
        fn = "Game [dlc pack] [0100AAA111222000][v0].nsp"
        # Title id ends in 000 but [dlc...] hint should override → dlc
        assert classify_file(Path(fn), fn) == "dlc"

    def test_real_user_files_classify_correctly(self):
        cases = {
            "Big Helmet Heroes [010044B01E786000][v0].nsp": "base",
            "Big Helmet Heroes [010044B01E786800][v131072].nsp": "update",
            "Yoku's Island Express [010002d00632e000][v0].nsp": "base",
            "Yoku's Island Express [UPD][010002d00632e800][v131072].nsp": "update",
            "ENDER LILIES Quietus of the Knights [0100CCF012E9A000][v0][Base].nsz": "base",
            "ENDER LILIES Quietus of the Knights [0100CCF012E9A800][v458752][Update].nsz": "update",
            "Portal Knights [DLC Bibot Box] [0100437004171003][v0].nsp": "dlc",
        }
        for fn, expected in cases.items():
            assert classify_file(Path(fn), fn) == expected, f"failed for {fn}"
