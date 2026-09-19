"""Локализация.

Исходный язык строк в коде — английский (msgid). Переводы лежат в ``po/``
и компилируются в ``locale/<lang>/LC_MESSAGES/rdp-launcher.mo``.

Если каталог перевода не собран, ``_()`` просто возвращает английский оригинал,
поэтому приложение работает и без компиляции.
"""
from __future__ import annotations

import gettext
import os
from pathlib import Path

DOMAIN = "rdp-launcher"
PACKAGE_DIR = Path(__file__).resolve().parent


def _locale_candidates() -> list[str]:
    candidates: list[str] = []
    override = os.environ.get("RDP_LAUNCHER_LOCALEDIR")
    if override:
        candidates.append(override)
    # из исходников: <проект>/locale
    candidates.append(str(PACKAGE_DIR.parent / "locale"))
    # установленный пакет / системный каталог
    candidates.append(str(PACKAGE_DIR / "locale"))
    candidates.append("/usr/share/locale")
    candidates.append("/usr/local/share/locale")
    return candidates


def _install() -> "gettext.NullTranslations":
    for directory in _locale_candidates():
        if os.path.isdir(directory):
            try:
                return gettext.translation(DOMAIN, directory, fallback=True)
            except OSError:
                continue
    return gettext.NullTranslations()


_translation = _install()
_: "gettext.NullTranslations.gettext" = _translation.gettext

__all__ = ["_", "DOMAIN"]
