"""
Top-level PyInstaller launcher for Switch Queue Copy.

Why this file exists
--------------------
When you run ``python -m switch_queue`` the interpreter sets
``__package__ = "switch_queue"`` on the ``__main__.py`` module, so the
relative import ``from .app import App`` resolves correctly.

PyInstaller does **not** preserve that semantics. If you point it at
``switch_queue/__main__.py`` directly, the bundled script runs as a
plain top-level module with no parent package — relative imports raise
``ImportError: attempted relative import with no known parent package``.

This tiny wrapper sidesteps the issue: as a top-level script it does an
absolute import of ``switch_queue.__main__.main``, and from inside the
package the relative imports work fine. ``flet pack`` is pointed at
this file (see ``scripts/build_exe.ps1`` and
``.github/workflows/release.yml``).

For development you still use ``python -m switch_queue``.
"""

from switch_queue.__main__ import main

if __name__ == "__main__":
    main()
