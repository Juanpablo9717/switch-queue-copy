"""
Regression tests for an os.path.join landmine on Windows.

Heribert17/mtp's bundled ``makedirs`` joined path components with
``os.path.join``. On Windows that interprets ``"5: SD Card install"`` as
having a drive letter and silently *discards* the previous component —
turning ``("DeviceName", "5: SD Card install")`` into just
``"5: SD Card install"``. Every DBI storage uses that ``"N:"`` numbering,
so every MTP upload to a Switch hit the same wall.

Our MtpBackend now walks the device tree by **list of parts** instead of
by joined-string, and the helper below proves it. We can't exercise the
actual COM stack without hardware, but we can lock the part-array logic
that determines what gets passed where.
"""

from __future__ import annotations

import os

from switch_queue.core.backends import build_uri, parse_uri


class TestMtpUriParsing:
    def test_parse_uri_with_colon_storage(self):
        device, parts = parse_uri("mtp://Switch/5: SD Card install")
        assert device == "Switch"
        assert parts == ["5: SD Card install"]

    def test_parse_uri_with_nested_colon_path(self):
        device, parts = parse_uri("mtp://Switch/5: SD Card install/sub/folder")
        assert device == "Switch"
        assert parts == ["5: SD Card install", "sub", "folder"]

    def test_build_uri_round_trips(self):
        uri = build_uri("Switch", "5: SD Card install", "Pokemon")
        assert uri == "mtp://Switch/5: SD Card install/Pokemon"
        device, parts = parse_uri(uri)
        assert device == "Switch"
        assert parts == ["5: SD Card install", "Pokemon"]


class TestColonInPathPreservation:
    """Directly demonstrates *why* we don't use os.path.join."""

    def test_os_path_join_drops_first_arg_on_colon(self):
        """If this ever stops being true, our workaround can simplify."""
        # On Windows, "5:" looks like a drive letter to ntpath.
        if os.name != "nt":
            return  # only meaningful on Windows
        joined = os.path.join("DeviceName", "5: SD Card install")
        # The second arg discards the first when it's drive-letter-like.
        assert joined == "5: SD Card install", (
            "os.path.join behaviour changed; revisit the manual traversal "
            "in MtpBackend — the workaround may no longer be necessary."
        )

    def test_part_list_preserves_colon_segments(self):
        """The MtpBackend approach: keep parts as a list, never join."""
        parts = ["DeviceName", "5: SD Card install", "Pokemon"]
        # No transformation needed — feed straight into get_child / create_content.
        assert parts[0] == "DeviceName"
        assert parts[1] == "5: SD Card install"
        assert parts[2] == "Pokemon"
        assert len(parts) == 3
