"""Lightweight i18n: locale dicts + ``t(key, **kwargs)`` translator."""

from .translator import LANGUAGE_LABELS, LOCALES, current_locale, set_locale, t

__all__ = ["t", "set_locale", "current_locale", "LOCALES", "LANGUAGE_LABELS"]
