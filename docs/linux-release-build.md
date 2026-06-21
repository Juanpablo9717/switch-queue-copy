# Known issue: Linux release binary (AppImage) does not build

> **Status:** broken since the AppImage migration (May 2026). Tagged
> releases publish the **Windows `.exe` only**; no Linux binary ships.
> Windows builds fine. This is a **CI/packaging** problem, unrelated to
> the app code. Running from source on Linux works perfectly.

## Symptom

The `Build AppImage (Linux only)` step in
[`.github/workflows/release.yml`](../.github/workflows/release.yml) fails:

```
::error::Could not locate Flutter bundle dir under build/linux/
##[error]Process completed with exit code 1.
```

Seen on tag `v0.2.0` (run `27884309890`) and the earlier `v0.1.0`-era
release attempts (e.g. the failed `Release` run on 2026-05-26).

## Root cause

The AppImage step expects the Flutter desktop bundle at
`build/linux/x64/release/bundle/` (Flutter convention) and runs
`find build/linux -type d -name bundle`. That returns **nothing**.

What `flet build linux` actually produced (from the run log) is only the
**serious_python** packaging — no Flutter desktop runtime:

```
build/linux/python3.12/...        # Python stdlib
build/linux/site-packages/...     # deps
build/linux/lib
build/linux/switch_queue_copy     # app sources
# (no  build/linux/x64/release/bundle/  and no compiled binary)
```

So `flet build linux` reported success but **did not compile the Flutter
Linux client** — likely the Flutter SDK/toolchain step didn't run to
completion on the runner, or this flet version changed the output layout
/ requires different flags. The downstream AppImage packaging then has
nothing to wrap.

## Possible solutions (in rough order of effort)

1. **Revert the Linux build to `flet pack`** (how `v0.1.0` successfully
   shipped a Linux binary). Simplest and proven. Mirror the Windows step:
   `flet pack main.py --name "Switch Queue Copy" ...`, then upload the
   `dist/` binary directly (drop the AppImage wrapper).
   - **Trade-off:** PyInstaller Linux binaries can hit `libpango` /
     `fontconfig` / `glibc` ABI mismatches on newer rolling distros
     (Arch, CachyOS, Fedora 41+) — the exact breakage the AppImage
     migration was meant to fix. Acceptable if "ships and runs on most
     distros" beats "never ships".

2. **Fix `flet build linux`** so it emits the Flutter bundle:
   - Confirm the Flutter SDK is actually installed/compiled on the runner
     (the step auto-downloads it to `$HOME/flutter/`; check that sub-step
     didn't fail silently). Consider pinning a known-good Flutter + flet
     version.
   - Verify the real output path on the current flet version (it may now
     be `build/linux/<arch>/release/bundle/` with a different arch dir, or
     elsewhere) and update the `find ... -name bundle` discovery + the
     AppImage `BUNDLE_DIR`/`BUNDLE_BIN` detection accordingly.
   - Add `set -x` / `ls -R build/` diagnostics to a throwaway run to map
     the layout before committing a fix.

3. **Ship source-only on Linux** (document the `uv` + `flet-desktop` run
   recipe from the README) and drop the Linux binary from releases until
   one of the above lands. Lowest effort, worst UX.

## Notes for whoever picks this up

- Iterating requires pushing to CI (the Flutter/GTK build can't be
  reproduced trivially on a dev box). Test on a throwaway pre-release tag
  like `v0.0.0-test1` (the workflow accepts `-suffix` SemVer) so you don't
  churn real release tags.
- The release action (`softprops/action-gh-release`) uploads per-job, so
  a green Windows job still publishes its asset even while the Linux job
  fails — which is why `v0.2.0` exists as Windows-only.
- Once fixed, recut the release so it carries **both** assets like
  `v0.1.0` did.
