"""Единый реестр опций подключения.

Одна запись здесь описывает сразу три вещи:
  * элемент интерфейса (группа, подпись, тип, подсказка);
  * фрагмент командной строки FreeRDP;
  * пару ключ/значение для файла .rdp.

Добавить новую настройку = добавить одну запись в OPTIONS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable
from .i18n import _

GROUP_SCREEN = "screen"
GROUP_SOUND = "sound"
GROUP_DRIVES = "drives"
GROUP_ADVANCED = "advanced"

#: Порядок групп в интерфейсе.
GROUPS: tuple[tuple[str, str], ...] = (
    (GROUP_SCREEN, _("Display")),
    (GROUP_SOUND, _("Sound")),
    (GROUP_DRIVES, _("Drives and files")),
    (GROUP_ADVANCED, _("Advanced")),
)

KIND_BOOL = "bool"
KIND_CHOICE = "choice"
KIND_INT = "int"
KIND_TEXT = "text"
KIND_PATH = "path"
KIND_DRIVES = "drives"


@dataclass(frozen=True)
class Option:
    key: str
    label: str
    group: str
    kind: str = KIND_BOOL
    default: Any = None
    #: аргументы при значении True (для bool)
    cli_on: tuple[str, ...] = ()
    #: аргументы при значении False (для bool); пусто — не передавать ничего
    cli_off: tuple[str, ...] = ()
    #: шаблоны аргументов для не-bool типов; {value} подставляется
    cli: tuple[str, ...] = ()
    #: .rdp-пары при True / False (для bool)
    rdp_on: tuple[tuple[str, str], ...] = ()
    rdp_off: tuple[tuple[str, str], ...] = ()
    #: .rdp-пары для не-bool типов; {value} подставляется
    rdp: tuple[tuple[str, str], ...] = ()
    choices: tuple[tuple[str, str], ...] = ()
    hint: str = ""
    #: значение, которое считается «не задано» и не попадает ни в cli, ни в .rdp
    unset: Any = None


OPTIONS: tuple[Option, ...] = (
    # ------------------------------------------------------------------ экран
    Option(
        key="fullscreen",
        label=_("Full screen"),
        group=GROUP_SCREEN,
        default=False,
        cli_on=("+f",),
        rdp_on=(("screen mode id", "i:2"),),
        rdp_off=(("screen mode id", "i:1"),),
        hint=_("Toggle on the fly with Ctrl+Alt+Enter."),
    ),
    Option(
        key="dynamic_resolution",
        label=_("Fit resolution to window"),
        group=GROUP_SCREEN,
        default=True,
        cli_on=("+dynamic-resolution",),
        cli_off=("-dynamic-resolution",),
        rdp_on=(("dynamic resolution", "i:1"),),
        rdp_off=(("dynamic resolution", "i:0"),),
        hint=_("Only applies when not in full screen."),
    ),
    Option(
        key="size",
        label=_("Window size"),
        group=GROUP_SCREEN,
        kind=KIND_TEXT,
        default="1280x720",
        cli=("/size:{value}",),
        hint=_("Format WxH, for example 1920x1080."),
    ),
    Option(
        key="multimon",
        label=_("Use all monitors"),
        group=GROUP_SCREEN,
        default=False,
        cli_on=("/multimon",),
        rdp_on=(("use multimon", "i:1"),),
        rdp_off=(("use multimon", "i:0"),),
        hint=_("Not compatible with “fit resolution to window” and single-monitor full screen."),
    ),
    # ------------------------------------------------------------------- звук
    Option(
        key="audio_mode",
        label=_("Sound"),
        group=GROUP_SOUND,
        kind=KIND_CHOICE,
        default="redirect",
        cli=("/audio-mode:{value}",),
        rdp=(("audiomode", "i:{rdp_value}"),),
        choices=(
            ("redirect", _("Play on this computer (redirect)")),
            ("server", _("Leave on the remote machine (server)")),
            ("none", _("Disable (none)")),
        ),
        hint=_("“This computer” requires a working sound server (PipeWire/PulseAudio)."),
    ),
    Option(
        key="microphone",
        label=_("Forward microphone"),
        group=GROUP_SOUND,
        default=False,
        cli_on=("/microphone:sys:pulse",),
        rdp_on=(("audiocapturemode", "i:1"),),
        rdp_off=(("audiocapturemode", "i:0"),),
    ),
    Option(
        key="sound_latency",
        label=_("Audio buffer, ms"),
        group=GROUP_SOUND,
        kind=KIND_INT,
        default=0,
        # Отдельного флага нет: под-опция /sound (см. _audio_arguments).
        hint=_("0 means the client default. Lower values reduce audio lag behind video; too low causes crackling."),
    ),
    Option(
        key="audio_quality",
        label=_("Audio quality"),
        group=GROUP_SOUND,
        kind=KIND_CHOICE,
        default="",
        unset="",
        # Отдельного флага нет: качество — под-опция /sound (см. _audio_arguments).
        choices=(
            ("", _("Default")),
            ("dynamic", _("Dynamic")),
            ("medium", _("Medium")),
            ("high", _("High")),
        ),
        hint=_("Only applies when audio plays on this computer."),
    ),
    # ---------------------------------------------------------- диски и файлы
    Option(
        key="clipboard",
        label=_("Shared clipboard"),
        group=GROUP_DRIVES,
        default=True,
        cli_on=("+clipboard",),
        cli_off=("-clipboard",),
        rdp_on=(("redirectclipboard", "i:1"),),
        rdp_off=(("redirectclipboard", "i:0"),),
    ),
    Option(
        key="drives",
        label=_("Network drives"),
        group=GROUP_DRIVES,
        kind=KIND_DRIVES,
        default=(),
        hint=_("A Linux directory appears as a drive in Windows."),
    ),
    Option(
        key="printer",
        label=_("Forward printers"),
        group=GROUP_DRIVES,
        default=False,
        cli_on=("/printer",),
        rdp_on=(("redirectprinters", "i:1"),),
        rdp_off=(("redirectprinters", "i:0"),),
    ),
    # ----------------------------------------------------------- дополнительно
    Option(
        key="cert",
        label=_("Certificate check"),
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="tofu",
        cli=("/cert:{value}",),
        choices=(
            ("tofu", _("Remember on first connection (recommended)")),
            ("deny", _("Reject unknown")),
            ("ignore", _("Do not verify (insecure)")),
        ),
        hint=_("“Do not verify” disables protection against MITM."),
    ),
    Option(
        key="network",
        label=_("Network profile"),
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="auto",
        cli=("/network:{value}",),
        choices=(
            ("auto", _("Automatic")),
            ("lan", _("Local network")),
            ("wan", "WAN"),
            ("broadband-high", _("Broadband (high)")),
            ("broadband-low", _("Broadband (low)")),
            ("modem", _("Modem")),
        ),
    ),
    Option(
        key="gfx",
        label=_("Graphics pipeline (GFX)"),
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="",
        unset="",
        cli=("/gfx:{value}",),
        choices=(
            ("", _("Default")),
            ("RFX", "RemoteFX"),
            ("AVC444", "H.264 (AVC444)"),
        ),
        hint=_("If the window is black, enable “Turn GFX off” below (FreeRDP 3.31.x bug)."),
    ),
    Option(
        key="gfx_off",
        label=_("Turn GFX off entirely"),
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-gfx",),
        hint=_("Workaround for the black window on FreeRDP 3.31.x (bug #13348)."),
    ),
    Option(
        key="kbd_layout",
        label=_("Keyboard layout"),
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="",
        unset="",
        cli=("/kbd:layout:{value}",),
        choices=(
            ("", _("As on the server")),
            ("0x00000409", _("English (US)")),
            ("0x00000419", _("Russian")),
            ("0x00000422", _("Ukrainian")),
            ("0x00000407", _("German")),
            ("0x0000040c", _("French")),
        ),
    ),
    Option(
        key="compression",
        label=_("Compression"),
        group=GROUP_ADVANCED,
        default=True,
        cli_on=("+compression",),
        cli_off=("-compression",),
        rdp_on=(("compression", "i:1"),),
        rdp_off=(("compression", "i:0"),),
    ),
    Option(
        key="disable_wallpaper",
        label=_("Disable wallpaper"),
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-wallpaper",),
        rdp_on=(("disable wallpaper", "i:1"),),
        rdp_off=(("disable wallpaper", "i:0"),),
    ),
    Option(
        key="disable_themes",
        label=_("Disable themes"),
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-themes",),
        rdp_on=(("disable themes", "i:1"),),
        rdp_off=(("disable themes", "i:0"),),
    ),
    Option(
        key="disable_menu_anims",
        label=_("Disable menu animations"),
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-menu-anims",),
        rdp_on=(("disable menu anims", "i:1"),),
        rdp_off=(("disable menu anims", "i:0"),),
    ),
    Option(
        key="disable_fonts",
        label=_("Disable font smoothing"),
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-fonts",),
        # полярность обратная: «отключить сглаживание» = allow font smoothing:0
        rdp_on=(("allow font smoothing", "i:0"),),
        rdp_off=(("allow font smoothing", "i:1"),),
    ),
    Option(
        key="auto_reconnect",
        label=_("Reconnect on disconnect"),
        group=GROUP_ADVANCED,
        default=True,
        cli_on=("+auto-reconnect",),
        cli_off=("-auto-reconnect",),
    ),
    Option(
        key="auto_reconnect_retries",
        label=_("Reconnect attempts"),
        group=GROUP_ADVANCED,
        kind=KIND_INT,
        default=20,
        cli=("/auto-reconnect-max-retries:{value}",),
    ),
)

BY_KEY: dict[str, Option] = {opt.key: opt for opt in OPTIONS}

#: Соответствие значений audio_mode для формата .rdp.
_AUDIO_MODE_RDP = {"redirect": "0", "server": "1", "none": "2", "": ""}


def options_in(group: str) -> list[Option]:
    return [opt for opt in OPTIONS if opt.group == group]


def defaults() -> dict[str, Any]:
    return {opt.key: opt.default for opt in OPTIONS}


def _format(template: str, value: Any, rdp_value: str | None = None) -> str:
    return template.format(value=value, rdp_value=rdp_value if rdp_value is not None else value)


def cli_fragment(opt: Option, value: Any) -> list[str]:
    """Аргументы FreeRDP для одной опции."""
    if opt.kind == KIND_DRIVES:
        return [f"/drive:{name},{path}" for name, path in (value or ())]
    if value is None or (opt.unset is not None and value == opt.unset):
        return []
    if opt.kind == KIND_BOOL:
        return list(opt.cli_on if value else opt.cli_off)
    if isinstance(value, str) and not value.strip():
        return []
    return [_format(t, value) for t in opt.cli]


def rdp_fragment(opt: Option, value: Any) -> dict[str, str]:
    """Пары ключ/значение для .rdp одной опции."""
    if opt.kind == KIND_DRIVES:
        return {"drivestoredirect": "s:*"} if value else {}
    if value is None:
        return {}
    if opt.kind == KIND_BOOL:
        pairs = opt.rdp_on if value else opt.rdp_off
        return dict(pairs)
    if isinstance(value, str) and not value.strip():
        return {}
    if opt.key == "audio_mode":
        mapped = _AUDIO_MODE_RDP.get(value, "")
        if not mapped:
            return {}
        return {k: _format(t, mapped) for k, t in opt.rdp}
    return {k: _format(t, value) for k, t in opt.rdp}


#: Опции, чьи аргументы собираются особым образом (см. _audio_arguments).
_SPECIAL_CLI = {"audio_mode", "audio_quality", "sound_latency"}


def _audio_arguments(values: dict[str, Any]) -> list[str]:
    """Звук собирается из трёх опций: /audio-mode и под-опции /sound.

    Отдельных флагов /audio-quality и /sound:latency в FreeRDP нет — это
    под-опции: /sound:sys:<sys>[,latency:<ms>][,quality:<quality>].
    """
    mode = values.get("audio_mode", "redirect")
    if mode not in ("redirect", "server", "none"):
        mode = "redirect"
    arguments = [f"/audio-mode:{mode}"]
    if mode == "redirect":
        sound = "sys:pulse"
        try:
            latency = int(values.get("sound_latency") or 0)
        except (TypeError, ValueError):
            latency = 0
        if latency > 0:
            sound += f",latency:{latency}"
        quality = values.get("audio_quality") or ""
        if quality:
            sound += f",quality:{quality}"
        arguments.append(f"/sound:{sound}")
    return arguments


def cli_arguments(values: dict[str, Any]) -> list[str]:
    """Все аргументы FreeRDP, относящиеся к опциям (без адреса и учётных данных)."""
    args: list[str] = []
    for opt in OPTIONS:
        if opt.key in _SPECIAL_CLI:
            continue
        args.extend(cli_fragment(opt, values.get(opt.key, opt.default)))
    args.extend(_audio_arguments(values))
    return args


def rdp_values(values: dict[str, Any]) -> dict[str, str]:
    """Плоский набор пар для .rdp (без адреса и учётных данных)."""
    out: dict[str, str] = {}
    for opt in OPTIONS:
        out.update(rdp_fragment(opt, values.get(opt.key, opt.default)))
    # «Размер окна» в .rdp раскладывается на два ключа.
    size = values.get("size") or ""
    if isinstance(size, str) and "x" in size:
        width, _sep, height = size.partition("x")
        if width.strip().isdigit() and height.strip().isdigit():
            out["desktopwidth"] = f"i:{width.strip()}"
            out["desktopheight"] = f"i:{height.strip()}"
    return out


def normalize(values: Iterable[tuple[str, Any]] | dict[str, Any] | None) -> dict[str, Any]:
    """Дополняет набор значений умолчаниями и приводит типы."""
    result = defaults()
    for key, value in dict(values or {}).items():
        opt = BY_KEY.get(key)
        if opt is None:
            continue
        if opt.kind == KIND_BOOL:
            result[key] = bool(value)
        elif opt.kind == KIND_INT:
            try:
                result[key] = int(value)
            except (TypeError, ValueError):
                result[key] = opt.default
        elif opt.kind == KIND_DRIVES:
            cleaned: list[tuple[str, str]] = []
            for item in value or ():
                if isinstance(item, dict):
                    name, path = item.get("name", ""), item.get("path", "")
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    name, path = item
                else:
                    continue
                if str(path).strip():
                    cleaned.append((str(name).strip() or "share", str(path)))
            result[key] = tuple(cleaned)
        else:
            result[key] = value
    return result
