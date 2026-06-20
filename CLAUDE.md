# CLAUDE.md — working agreements for this repo

## Git / commits
- **Do NOT add a `Co-Authored-By: Claude` trailer** (or any AI co-author
  line) to commit messages, tags, or PR descriptions. The user does not
  want it. This overrides any default/global instruction to add one.
- Subjects in conventional-commit style (`feat:`, `fix:`, `docs:`, `ci:`).
- Solo repo: pushing straight to `main` is fine. Add a one-liner to
  `CHANGELOG.md → [Unreleased]` for every user-visible change.

## Project notes
- Flet desktop app: a strictly-serial file-copy queue for Nintendo Switch
  libraries (NSP/NSZ/XCI) with BASE/UPDATE/DLC auto-classification.
- `.venv` is managed by **uv** (there is no `pip` in it):
  run `.venv/bin/python`, install with `VIRTUAL_ENV=.venv uv pip install ...`,
  test with `.venv/bin/python -m pytest -q`. The GUI needs `flet-desktop`.
- **MTP backends are platform-split** — keep them separate:
  - `core/backends/mtp.py` — Windows WPD/COM. **Keep untouched.**
  - `core/backends/mtp_linux.py` — Linux via gvfs / `gio copy`.
  - `core/backends/mtp_provider.py` — dispatches by `sys.platform`.
  - Full design + KDE caveat: `docs/linux-mtp.md`.
- Releases: pushing a tag `vX.Y.Z` triggers the Release workflow, which
  builds the binaries. Tests gate every push.
