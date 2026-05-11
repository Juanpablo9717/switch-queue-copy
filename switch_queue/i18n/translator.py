"""
Tiny i18n layer.

Each locale is a flat ``dict[str, str]`` (see ``es.py`` / ``en.py``).
Components call ``t("key", **kwargs)`` lazily, so on locale change the App
just calls ``set_locale(...)`` and rebuilds the UI.

Adding a new language:
    1. Create ``switch_queue/i18n/<code>.py`` exporting ``TRANSLATIONS``
    2. Register it in ``LOCALES`` and ``LANGUAGE_LABELS`` below
"""

from __future__ import annotations

from typing import Any

from . import en, es

# code → translation dict
LOCALES: dict[str, dict[str, str]] = {
    "es": es.TRANSLATIONS,
    "en": en.TRANSLATIONS,
}

# code → human label shown in the language picker
LANGUAGE_LABELS: dict[str, str] = {
    "es": "Español",
    "en": "English",
}

# Default locale (the user can change it from Settings).
current_locale: str = "es"


def set_locale(code: str) -> None:
    """Switch the active locale. Unknown codes are ignored."""
    global current_locale
    if code in LOCALES:
        current_locale = code


def t(key: str, **kwargs: Any) -> str:
    """
    Translate ``key`` to the current locale.

    If the key is missing in the current locale, falls back to ``es``,
    then to the key itself (so you'll see the key in the UI rather than
    crash). Use ``**kwargs`` for ``str.format`` placeholders.
    """
    text = LOCALES[current_locale].get(key)
    if text is None:
        text = LOCALES["es"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
