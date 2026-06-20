# MTP on Linux (gvfs + `gio copy`)

> How the **Dispositivo MTP** destination works on Linux, why it's built
> the way it is, and how to troubleshoot it. Windows MTP is unaffected by
> any of this — it keeps using the WPD/COM backend in
> [`switch_queue/core/backends/mtp.py`](../switch_queue/core/backends/mtp.py).

## TL;DR

- **Windows** talks to MTP through WPD/COM (`comtypes`). Destination is an
  `mtp://<device-name>/<storage>/...` URI handled by `MtpBackend`.
- **Linux** talks to MTP through the desktop's **gvfs** layer, driven by
  the `gio` CLI. Destination is an `mtp://<gvfs-host>/<storage>/...` URI
  handled by `LinuxMtpBackend`, which copies with **`gio copy`**.
- The Linux path adds **no new Python dependency** — it shells out to
  `gio`, which ships with GLib/GVFS on every mainstream desktop.

## Requirements (per user system)

| Need | Package |
| --- | --- |
| `gio` CLI | `glib2` (always present on GTK desktops) |
| gvfs MTP backend | **`gvfs-mtp`** (Arch/Fedora) · **`gvfs-backends`** (Debian/Ubuntu) |

`gvfs-mtp` is **not bundled** in the AppImage (it's a system service that
claims the USB device), so the user installs it once from their package
manager. If it's missing, the picker shows an actionable hint instead of
failing silently (i18n key `picker.mtp_install_hint`).

## Why not just reuse `LocalBackend`?

When gvfs mounts an MTP device it appears as an ordinary directory:

```
/run/user/<uid>/gvfs/mtp:host=<id>/<storage>/...
```

Writing there with Python `open(dst, "wb")` **works for ordinary
storages** (the SD card, NAND, Album…) but **fails for DBI's "install"
storages** (`5: SD Card install`, `6: NAND install`):

```
OSError: [Errno 5] Input/output error
```

The reason: gvfs creates a **zero-byte object first** and then streams
bytes into it. DBI's install drop-zone rejects that — it can't even
create the object. (Empirically the `open()` itself fails, before a
single byte is sent.)

`gio copy` instead hands libmtp the file **with its size up front**
(`LIBMTP_Send_File_From_File`) — the same one-shot `SendObject` flow the
Windows WPD backend uses, and exactly what DBI expects. So:

- `gio copy` → DBI install works **and** ordinary storages work.
- It is therefore the single upload mechanism for every Linux MTP
  destination. `LocalBackend` is only used for true local folders.

## DBI install storages are flat

DBI's install storages contain a placeholder file
`Place NSP, NSZ, XCI, XCZ or MSP files here` and **do not accept
sub-folders** — files must arrive at the storage root. `LinuxMtpBackend`
detects an install storage (name contains `install`) and **drops the
source folder structure**, sending each file flat. Ordinary storages keep
the source folder structure, like the local backend.

After a successful install the file **disappears** from the storage
listing — that's DBI consuming it. Re-sending an already-installed title
makes DBI reject it (the upload errors after transferring), but this does
**not** wedge the session: the next file installs fine.

## How control maps onto `gio copy`

`gio copy` is a child process, so:

| Feature | Mechanism |
| --- | --- |
| Progress | parse `gio copy -p` stdout under `LC_ALL=C` (stable English: `Copied 5.5 MB out of 20.0 MB …`) |
| Pause | `SIGSTOP` the process; `SIGCONT` to resume |
| Cancel / Skip | terminate the process (`SIGCONT`→`SIGTERM`→`SIGKILL`) |
| Cleanup of a partial | `gio remove <mtp-uri>` |

## ⚠️ KDE caveat (device contention)

On **GNOME** gvfs auto-mounts the device on connect — zero friction.

On **KDE Plasma**, KIO (`kiod6`) grabs the MTP device the instant it's
connected and holds it, so `gio mount` fails with *"Could not open MTP
device"*. Symptom: the picker shows no device, or mounting errors.

Fix (pick one):

1. **Disable** *System Settings → Removable Storage → Removable Devices*
   automounting for MTP, then reconnect. gvfs can then claim it. (One-time.)
2. Reconnect the console after closing whatever holds it.
3. Manual unblock: `gio mount "mtp://<host>/"` after the KIO worker
   releases the device.

`kio-fuse` (KDE's FUSE bridge) **cannot** expose MTP as a folder either —
it explicitly rejects the `mtp` scheme — so KDE has no
plain-filesystem-path route; gvfs is the way.

## Code map

| File | Role |
| --- | --- |
| [`core/backends/mtp_linux.py`](../switch_queue/core/backends/mtp_linux.py) | gvfs discovery/mount + `LinuxMtpBackend` (`gio copy`) |
| [`core/backends/mtp_provider.py`](../switch_queue/core/backends/mtp_provider.py) | platform dispatch (Windows WPD vs Linux gvfs) |
| [`core/backends/mtp.py`](../switch_queue/core/backends/mtp.py) | Windows WPD backend — **unchanged** |
| [`ui/components/mtp_picker.py`](../switch_queue/ui/components/mtp_picker.py) | platform-agnostic picker (uses the provider) |
| [`tests/test_mtp_linux.py`](../tests/test_mtp_linux.py) | pure tests (mock `gio`, no device needed) |

## Known limitations / future work

- **`gio copy` reads the source size up front**, so progress is real but
  pause is process-level (a stopped child still holds the device).
- A file that fails mid-queue does **not** cascade in practice, but there
  is no automatic gvfs remount-to-reset if a session ever wedges.
- `file_exists_with_size` always returns `False` for install storages
  (files don't persist there), so re-running a queue re-sends everything;
  DBI rejects already-installed titles harmlessly.
- macOS has no gvfs; MTP is effectively unsupported there (the picker
  degrades to the install hint).
