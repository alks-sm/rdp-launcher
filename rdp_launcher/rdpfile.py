"""Чтение и запись файлов .rdp (формат Microsoft, понимают и Windows, и FreeRDP).

Пароли в .rdp не пишутся: они хранятся в связке ключей (см. secrets.py).
"""
from __future__ import annotations

from . import options as opts
from .model import Profile, DEFAULT_PORT
from .i18n import _

_RDP_TO_OPTION: dict[str, str] = {}
for _opt in opts.OPTIONS:
    for _pairs in (_opt.rdp_on, _opt.rdp_off, _opt.rdp):
        for _key, _rdp_value in _pairs:
            _RDP_TO_OPTION.setdefault(_key.lower(), _opt.key)

def _strip_type(value: str) -> str:
    """Убирает префикс типа (i:, s:, b:), сохраняя регистр значения."""
    head, sep, rest = value.partition(":")
    if sep and len(head) <= 1:
        return rest.strip()
    return value.strip()


#: Обратное соответствие для bool-опций: (ключ .rdp, значение) -> (ключ опции, bool).
_BOOL_BY_RDP: dict[tuple[str, str], tuple[str, bool]] = {}
for _opt in opts.OPTIONS:
    if _opt.kind != opts.KIND_BOOL:
        continue
    for _key, _value in _opt.rdp_on:
        _BOOL_BY_RDP[(_key.lower(), _strip_type(_value).lower())] = (_opt.key, True)
    for _key, _value in _opt.rdp_off:
        _BOOL_BY_RDP[(_key.lower(), _strip_type(_value).lower())] = (_opt.key, False)


def to_rdp_text(profile: Profile) -> str:
    """Профиль -> текст .rdp."""
    lines = [
        "; Created by RDP Launcher",
        f"full address:s:{profile.address}",
    ]
    if profile.username:
        lines.append(f"username:s:{profile.username}")
    if profile.domain:
        lines.append(f"domain:s:{profile.domain}")

    pairs = opts.rdp_values(profile.values)
    # Явный порядок ключей: так файл читаемее и стабильнее при диффах.
    order = [
        "screen mode id", "desktopwidth", "desktopheight", "dynamic resolution",
        "use multimon", "audiomode", "audiocapturemode", "redirectclipboard",
        "redirectprinters", "drivestoredirect", "compression", "disable wallpaper",
        "disable themes", "disable menu anims", "allow font smoothing",
    ]
    for key in order:
        if key in pairs:
            lines.append(f"{key}:{pairs.pop(key)}")
    for key, value in pairs.items():
        lines.append(f"{key}:{value}")
    return "\n".join(lines) + "\n"


def parse_rdp_text(text: str) -> Profile:
    """Текст .rdp -> профиль. Неизвестные ключи игнорируются."""
    raw: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        key, _sep, value = line.partition(":")
        key = key.strip().lower()
        # значение тоже имеет префикс типа: s:, i:, b:
        raw[key] = value.strip()

    address = _strip_type(raw.get("full address") or raw.get("alternate full address") or "")
    host, _sep, port = address.partition(":")
    profile = Profile(
        name=raw.get("name", "") or _("Imported connection"),
        host=host,
        port=int(port) if port.isdigit() else DEFAULT_PORT,
        username=_strip_type(raw.get("username", "")),
        domain=_strip_type(raw.get("domain", "")),
    )

    values = dict(profile.values)
    for key, raw_value in raw.items():
        value = _strip_type(raw_value)
        if (key, value.lower()) in _BOOL_BY_RDP:
            opt_key, bool_value = _BOOL_BY_RDP[(key, value.lower())]
            values[opt_key] = bool_value
            continue
        option_key = _RDP_TO_OPTION.get(key)
        if option_key is None:
            continue
        option = opts.BY_KEY[option_key]
        if option.kind == opts.KIND_BOOL:
            continue
        if option_key == "audio_mode":
            reverse = {"0": "redirect", "1": "server", "2": "none"}
            values[option_key] = reverse.get(value.lower(), option.default)
        else:
            values[option_key] = value

    width = _strip_type(raw.get("desktopwidth", ""))
    height = _strip_type(raw.get("desktopheight", ""))
    if width.isdigit() and height.isdigit():
        values["size"] = f"{width}x{height}"

    profile.values = opts.normalize(values)
    return profile
