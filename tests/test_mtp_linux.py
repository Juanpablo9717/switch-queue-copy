"""
Tests for the Linux gvfs MTP provider (``mtp_linux``).

These lock the pure logic — host normalization, ``gio mount -li`` parsing,
folder listing, and destination-path building — without needing a real
device or the ``gio`` binary. The module is Linux-only (it uses
``os.getuid`` and ``/run/user``), so the whole file is skipped on Windows,
mirroring how the WPD tests are gated the other way.

The headline invariant: on Linux an MTP destination is a **plain
filesystem path** under the gvfs mount, so ``make_backend`` routes it to
``LocalBackend`` — no MTP-specific copy code runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

if sys.platform == "win32":
    pytest.skip("Linux gvfs MTP provider is not used on Windows", allow_module_level=True)

from switch_queue.core.backends import mtp_linux as ml
from switch_queue.core.backends.mtp_linux import LinuxMtpBackend
from switch_queue.core.copier import make_backend


# Sample `gio mount -li` output with one MTP volume plus noise that must be
# ignored (a block device volume).
_GIO_LI = """\
Drive(0): Samsung SSD
  Type: GProxyDrive (GProxyVolumeMonitorUDisks2)
Volume(0): DBI
  Type: GProxyVolume (GProxyVolumeMonitorMTP)
  ids:
   unix-device: '/dev/bus/usb/003/008'
  activation_root=mtp://-_DBI_XTJ50380016740/
  themed icons:  [phone]
Volume(1): My USB
  Type: GProxyVolume (GProxyVolumeMonitorUDisks2)
  activation_root=file:///run/media/me/MYUSB/
"""


class TestHostNormalization:
    def test_mount_dir_and_root_compare_equal(self):
        host_from_mount = ml._host_of("mtp:host=-_DBI_XTJ50380016740")
        host_from_root = ml._host_of("mtp://-_DBI_XTJ50380016740/")
        assert host_from_mount == host_from_root == "-_DBI_XTJ50380016740"

    def test_url_encoded_root_is_decoded(self):
        # usb-form activation roots are percent-encoded.
        assert ml._host_of("mtp://%5Busb%3A003%2C008%5D/") == "[usb:003,008]"

    def test_friendly_name_from_host(self):
        assert ml._friendly("-_DBI_XTJ50380016740") == "DBI"
        assert ml._friendly("Galaxy") == "Galaxy"


class TestVolumeParsing:
    def test_only_mtp_volumes_are_returned(self, monkeypatch):
        class _Proc:
            stdout = _GIO_LI

        monkeypatch.setattr(ml.shutil, "which", lambda _: "/usr/bin/gio")
        monkeypatch.setattr(ml.subprocess, "run", lambda *a, **k: _Proc())

        vols = ml._list_mtp_volumes()
        assert vols == [("DBI", "mtp://-_DBI_XTJ50380016740/")]

    def test_no_gio_binary_raises_unavailable(self, monkeypatch):
        monkeypatch.setattr(ml.shutil, "which", lambda _: None)
        with pytest.raises(ml.MtpUnavailable):
            ml.list_devices()


class TestFolderListing:
    def test_lists_dirs_and_files_with_content_type(self, tmp_path: Path):
        dev = ml.LinuxMtpDevice(
            name="DBI", devicename="mtp:host=x", mount_path=tmp_path
        )
        (tmp_path / "1: SD Card").mkdir()
        (tmp_path / "boot.dat").write_bytes(b"x")

        entries = {e.name: e for e in ml.list_device_folders(dev, [])}
        assert entries["1: SD Card"].content_type == ml._DIR
        assert entries["boot.dat"].content_type == ml._FILE

    def test_missing_path_yields_nothing(self, tmp_path: Path):
        dev = ml.LinuxMtpDevice(
            name="DBI", devicename="mtp:host=x", mount_path=tmp_path
        )
        assert list(ml.list_device_folders(dev, ["does-not-exist"])) == []


class TestDestinationRouting:
    def test_build_destination_is_mtp_uri(self, tmp_path: Path):
        dev = ml.LinuxMtpDevice(
            name="DBI",
            devicename="mtp:host=-_DBI_XTJ50380016740",
            mount_path=tmp_path,
        )
        dest = ml.build_destination(dev, ["5: SD Card install", "Pokemon"])
        assert dest == "mtp://-_DBI_XTJ50380016740/5: SD Card install/Pokemon"

    def test_destination_routes_to_linux_mtp_backend(self, tmp_path: Path):
        # gio copy is required (DBI install storages reject plain writes), so
        # an MTP URI must route to LinuxMtpBackend, never LocalBackend.
        dev = ml.LinuxMtpDevice(
            name="DBI",
            devicename="mtp:host=-_DBI_XTJ50380016740",
            mount_path=tmp_path,
        )
        dest = ml.build_destination(dev, ["1: SD Card"])
        assert isinstance(make_backend(dest), LinuxMtpBackend)


class TestInstallStorageDetection:
    def test_install_storage_sends_flat(self):
        b = LinuxMtpBackend("mtp://host/5: SD Card install")
        assert b._is_install is True
        # rel_path (the game sub-folder) is dropped: files land flat.
        uri = b._target_file_uri(Path("Cadence of Hyrule [NSP]"), "game.nsp")
        assert uri == "mtp://host/5: SD Card install/game.nsp"

    def test_real_storage_preserves_structure(self):
        b = LinuxMtpBackend("mtp://host/1: SD Card")
        assert b._is_install is False
        uri = b._target_file_uri(Path("games/Zelda"), "game.nsp")
        assert uri == "mtp://host/1: SD Card/games/Zelda/game.nsp"


class TestProgressParsing:
    def test_parses_si_units(self):
        assert ml._parse_progress_bytes("Copied 5.5 MB out of 20.0 MB (x)") == 5_500_000
        assert ml._parse_progress_bytes("Copied 12 bytes out of 59.1 MB") == 12
        assert ml._parse_progress_bytes("Copied 1.5 kB out of 2.0 kB") == 1_500

    def test_ignores_non_progress_lines(self):
        assert ml._parse_progress_bytes("Copied 20.0 MB (average: 13.8 MB/s)") is None
        assert ml._parse_progress_bytes("some unrelated output") is None
