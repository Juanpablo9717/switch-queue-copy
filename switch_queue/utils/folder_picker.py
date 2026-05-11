"""
Native Windows multi-folder picker via IFileOpenDialog.

The modern Windows "Open" dialog (Vista+) supports both
``FOS_PICKFOLDERS`` (browse folders) and ``FOS_ALLOWMULTISELECT``
(Ctrl+Click / Shift+Click multi-select). Flet's ``get_directory_path``
uses the older, single-select-only dialog and never exposes those
flags, so we drive the COM API directly via ``comtypes``.

This module exposes a single function:

    pick_folders(title=..., initial_dir=...) -> list[Path]

Returns the user's selection (or ``[]`` if they cancelled). Falls back
to an empty list on non-Windows; callers should provide a custom UI
fallback in that case.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Non-Windows: no-op stub so imports stay safe in tests / dev on Linux/macOS.
# ---------------------------------------------------------------------------

if sys.platform != "win32":
    def pick_folders(title: str | None = None,
                     initial_dir: Path | str | None = None) -> list[Path]:
        return []

else:
    import ctypes
    from ctypes import POINTER, byref, c_uint, c_ulong, c_void_p, c_wchar_p

    import comtypes
    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
    from comtypes.client import CreateObject

    # -- Constants --------------------------------------------------------

    FOS_PICKFOLDERS = 0x00000020
    FOS_FORCEFILESYSTEM = 0x00000040
    FOS_ALLOWMULTISELECT = 0x00000200
    SIGDN_FILESYSPATH = 0x80058000

    CLSID_FileOpenDialog = GUID("{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}")
    IID_IShellItem = GUID("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")

    # -- COM interface definitions ---------------------------------------
    #
    # We have to declare every vtable slot up to the methods we call so the
    # offsets line up. Slots we don't use are typed loosely (c_void_p) but
    # still occupy the right vtable position.

    class IShellItem(IUnknown):
        _iid_ = IID_IShellItem
        _methods_ = [
            COMMETHOD([], HRESULT, "BindToHandler",
                      (["in"], c_void_p, "pbc"),
                      (["in"], POINTER(GUID), "bhid"),
                      (["in"], POINTER(GUID), "riid"),
                      (["out"], POINTER(c_void_p), "ppv")),
            COMMETHOD([], HRESULT, "GetParent",
                      (["out"], POINTER(c_void_p), "ppsi")),
            COMMETHOD([], HRESULT, "GetDisplayName",
                      (["in"], c_ulong, "sigdnName"),
                      (["out"], POINTER(c_wchar_p), "ppszName")),
            COMMETHOD([], HRESULT, "GetAttributes",
                      (["in"], c_ulong, "sfgaoMask"),
                      (["out"], POINTER(c_ulong), "psfgaoAttribs")),
            COMMETHOD([], HRESULT, "Compare",
                      (["in"], c_void_p, "psi"),
                      (["in"], c_ulong, "hint"),
                      (["out"], POINTER(c_uint), "piOrder")),
        ]

    class IShellItemArray(IUnknown):
        _iid_ = GUID("{B63EA76D-1F85-456F-A19C-48159EFA858B}")
        _methods_ = [
            COMMETHOD([], HRESULT, "BindToHandler",
                      (["in"], c_void_p, "pbc"),
                      (["in"], POINTER(GUID), "bhid"),
                      (["in"], POINTER(GUID), "riid"),
                      (["out"], POINTER(c_void_p), "ppvOut")),
            COMMETHOD([], HRESULT, "GetPropertyStore",
                      (["in"], c_ulong, "flags"),
                      (["in"], POINTER(GUID), "riid"),
                      (["out"], POINTER(c_void_p), "ppv")),
            COMMETHOD([], HRESULT, "GetPropertyDescriptionList",
                      (["in"], c_void_p, "keyType"),
                      (["in"], POINTER(GUID), "riid"),
                      (["out"], POINTER(c_void_p), "ppv")),
            COMMETHOD([], HRESULT, "GetAttributes",
                      (["in"], c_ulong, "AttribFlags"),
                      (["in"], c_ulong, "sfgaoMask"),
                      (["out"], POINTER(c_ulong), "psfgaoAttribs")),
            COMMETHOD([], HRESULT, "GetCount",
                      (["out"], POINTER(c_ulong), "pdwNumItems")),
            COMMETHOD([], HRESULT, "GetItemAt",
                      (["in"], c_ulong, "dwIndex"),
                      (["out"], POINTER(POINTER(IShellItem)), "ppsi")),
            COMMETHOD([], HRESULT, "EnumItems",
                      (["out"], POINTER(c_void_p), "ppenumShellItems")),
        ]

    class IFileDialog(IUnknown):
        # IID for IFileDialog (parent of IFileOpenDialog).
        _iid_ = GUID("{42F85136-DB7E-439C-85F1-E4075D135FC8}")
        _methods_ = [
            # IModalWindow
            COMMETHOD([], HRESULT, "Show",
                      (["in"], c_void_p, "hwndOwner")),
            # IFileDialog
            COMMETHOD([], HRESULT, "SetFileTypes",
                      (["in"], c_uint, "cFileTypes"),
                      (["in"], c_void_p, "rgFilterSpec")),
            COMMETHOD([], HRESULT, "SetFileTypeIndex",
                      (["in"], c_uint, "iFileType")),
            COMMETHOD([], HRESULT, "GetFileTypeIndex",
                      (["out"], POINTER(c_uint), "piFileType")),
            COMMETHOD([], HRESULT, "Advise",
                      (["in"], c_void_p, "pfde"),
                      (["out"], POINTER(c_ulong), "pdwCookie")),
            COMMETHOD([], HRESULT, "Unadvise",
                      (["in"], c_ulong, "dwCookie")),
            COMMETHOD([], HRESULT, "SetOptions",
                      (["in"], c_ulong, "fos")),
            COMMETHOD([], HRESULT, "GetOptions",
                      (["out"], POINTER(c_ulong), "pfos")),
            COMMETHOD([], HRESULT, "SetDefaultFolder",
                      (["in"], POINTER(IShellItem), "psi")),
            COMMETHOD([], HRESULT, "SetFolder",
                      (["in"], POINTER(IShellItem), "psi")),
            COMMETHOD([], HRESULT, "GetFolder",
                      (["out"], POINTER(POINTER(IShellItem)), "ppsi")),
            COMMETHOD([], HRESULT, "GetCurrentSelection",
                      (["out"], POINTER(POINTER(IShellItem)), "ppsi")),
            COMMETHOD([], HRESULT, "SetFileName",
                      (["in"], c_wchar_p, "pszName")),
            COMMETHOD([], HRESULT, "GetFileName",
                      (["out"], POINTER(c_wchar_p), "pszName")),
            COMMETHOD([], HRESULT, "SetTitle",
                      (["in"], c_wchar_p, "pszTitle")),
            COMMETHOD([], HRESULT, "SetOkButtonLabel",
                      (["in"], c_wchar_p, "pszText")),
            COMMETHOD([], HRESULT, "SetFileNameLabel",
                      (["in"], c_wchar_p, "pszLabel")),
            COMMETHOD([], HRESULT, "GetResult",
                      (["out"], POINTER(POINTER(IShellItem)), "ppsi")),
            COMMETHOD([], HRESULT, "AddPlace",
                      (["in"], POINTER(IShellItem), "psi"),
                      (["in"], c_uint, "fdap")),
            COMMETHOD([], HRESULT, "SetDefaultExtension",
                      (["in"], c_wchar_p, "pszDefaultExtension")),
            COMMETHOD([], HRESULT, "Close",
                      (["in"], c_ulong, "hr")),
            COMMETHOD([], HRESULT, "SetClientGuid",
                      (["in"], POINTER(GUID), "guid")),
            COMMETHOD([], HRESULT, "ClearClientData"),
            COMMETHOD([], HRESULT, "SetFilter",
                      (["in"], c_void_p, "pFilter")),
        ]

    class IFileOpenDialog(IFileDialog):
        _iid_ = GUID("{D57C7288-D4AD-4768-BE02-9D969532D960}")
        _methods_ = [
            COMMETHOD([], HRESULT, "GetResults",
                      (["out"], POINTER(POINTER(IShellItemArray)), "ppenum")),
            COMMETHOD([], HRESULT, "GetSelectedItems",
                      (["out"], POINTER(POINTER(IShellItemArray)), "ppsai")),
        ]

    # -- Helper to convert a path to an IShellItem (for initial folder) ---

    _shell32 = ctypes.windll.shell32
    _SHCreateItemFromParsingName = _shell32.SHCreateItemFromParsingName
    _SHCreateItemFromParsingName.argtypes = [
        c_wchar_p, c_void_p, POINTER(GUID), POINTER(c_void_p)
    ]
    _SHCreateItemFromParsingName.restype = ctypes.c_int  # HRESULT

    def _shell_item_from_path(path: str) -> "POINTER(IShellItem) | None":
        out = c_void_p()
        hr = _SHCreateItemFromParsingName(path, None, IID_IShellItem, byref(out))
        if hr != 0 or not out.value:
            return None
        return ctypes.cast(out, POINTER(IShellItem))

    # -- Public API -------------------------------------------------------

    def pick_folders(title: str | None = None,
                     initial_dir: Path | str | None = None) -> list[Path]:
        """Show the native multi-folder picker. Returns selected paths.

        Empty list means cancelled. Any COM error is swallowed and returned
        as an empty list — the caller should fall back to a custom UI.
        """
        try:
            comtypes.CoInitialize()
        except OSError:
            pass

        try:
            dialog = CreateObject(CLSID_FileOpenDialog, interface=IFileOpenDialog)

            current = dialog.GetOptions()
            dialog.SetOptions(
                current
                | FOS_PICKFOLDERS
                | FOS_ALLOWMULTISELECT
                | FOS_FORCEFILESYSTEM
            )

            if title:
                dialog.SetTitle(title)

            if initial_dir:
                init_str = str(Path(initial_dir).resolve())
                item = _shell_item_from_path(init_str)
                if item is not None:
                    try:
                        dialog.SetFolder(item)
                    except comtypes.COMError:
                        pass  # not fatal — dialog opens in default folder

            try:
                dialog.Show(None)
            except comtypes.COMError as exc:
                # 0x800704C7 == ERROR_CANCELLED. Python sees it as a negative
                # signed int (-2147023673) — user clicked Cancel, not an error.
                if exc.hresult in (-2147023673, 0x800704C7):
                    return []
                raise

            results = dialog.GetResults()
            count = c_ulong()
            # comtypes auto-unwraps single-out params, so this is fine:
            count_value = results.GetCount()

            paths: list[Path] = []
            for i in range(count_value):
                item = results.GetItemAt(i)
                name = item.GetDisplayName(SIGDN_FILESYSPATH)
                if name:
                    paths.append(Path(name))
            return paths
        except Exception:
            return []
        finally:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass
