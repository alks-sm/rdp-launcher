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

GROUP_SCREEN = "screen"
GROUP_SOUND = "sound"
GROUP_DRIVES = "drives"
GROUP_ADVANCED = "advanced"

#: Порядок групп в интерфейсе.
GROUPS: tuple[tuple[str, str], ...] = (
    (GROUP_SCREEN, "Экран"),
    (GROUP_SOUND, "Звук"),
    (GROUP_DRIVES, "Диски и файлы"),
    (GROUP_ADVANCED, "Дополнительно"),
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
        label="Полный экран",
        group=GROUP_SCREEN,
        default=False,
        cli_on=("+f",),
        rdp_on=(("screen mode id", "i:2"),),
        rdp_off=(("screen mode id", "i:1"),),
        hint="Переключение на лету: Ctrl+Alt+Enter.",
    ),
    Option(
        key="dynamic_resolution",
        label="Подстраивать разрешение под окно",
        group=GROUP_SCREEN,
        default=True,
        cli_on=("+dynamic-resolution",),
        cli_off=("-dynamic-resolution",),
        rdp_on=(("dynamic resolution", "i:1"),),
        rdp_off=(("dynamic resolution", "i:0"),),
        hint="Работает только вне полного экрана.",
    ),
    Option(
        key="size",
        label="Размер окна",
        group=GROUP_SCREEN,
        kind=KIND_TEXT,
        default="1280x720",
        cli=("/size:{value}",),
        hint="Формат ШxВ, например 1920x1080.",
    ),
    Option(
        key="multimon",
        label="Использовать все мониторы",
        group=GROUP_SCREEN,
        default=False,
        cli_on=("/multimon",),
        rdp_on=(("use multimon", "i:1"),),
        rdp_off=(("use multimon", "i:0"),),
        hint="Несовместимо с «подстраивать разрешение» и полным экраном в один монитор.",
    ),
    # ------------------------------------------------------------------- звук
    Option(
        key="audio_mode",
        label="Звук",
        group=GROUP_SOUND,
        kind=KIND_CHOICE,
        default="redirect",
        cli=("/audio-mode:{value}",),
        rdp=(("audiomode", "i:{rdp_value}"),),
        choices=(
            ("redirect", "Воспроизводить здесь (redirect)"),
            ("server", "Оставить на удалённой машине (server)"),
            ("none", "Отключить (none)"),
        ),
        hint="«Здесь» требует рабочего звукового сервера (PipeWire/PulseAudio).",
    ),
    Option(
        key="microphone",
        label="Передавать микрофон",
        group=GROUP_SOUND,
        default=False,
        cli_on=("/microphone:sys:pulse",),
        rdp_on=(("audiocapturemode", "i:1"),),
        rdp_off=(("audiocapturemode", "i:0"),),
    ),
    Option(
        key="sound_latency",
        label="Буферизация звука, мс",
        group=GROUP_SOUND,
        kind=KIND_INT,
        default=0,
        # Отдельного флага нет: под-опция /sound (см. _audio_arguments).
        hint="0 — как в клиенте. Меньше значение — меньше отставание звука от картинки, "
        "но при слишком малом появляются щелчки.",
    ),
    Option(
        key="audio_quality",
        label="Качество звука",
        group=GROUP_SOUND,
        kind=KIND_CHOICE,
        default="",
        unset="",
        # Отдельного флага нет: качество — под-опция /sound (см. _audio_arguments).
        choices=(
            ("", "По умолчанию"),
            ("dynamic", "Динамическое"),
            ("medium", "Среднее"),
            ("high", "Высокое"),
        ),
        hint="Применяется только при выводе звука здесь.",
    ),
    # ---------------------------------------------------------- диски и файлы
    Option(
        key="clipboard",
        label="Общий буфер обмена",
        group=GROUP_DRIVES,
        default=True,
        cli_on=("+clipboard",),
        cli_off=("-clipboard",),
        rdp_on=(("redirectclipboard", "i:1"),),
        rdp_off=(("redirectclipboard", "i:0"),),
    ),
    Option(
        key="drives",
        label="Сетевые диски",
        group=GROUP_DRIVES,
        kind=KIND_DRIVES,
        default=(),
        hint="Каталог Linux появится как диск в Windows.",
    ),
    Option(
        key="printer",
        label="Пробрасывать принтеры",
        group=GROUP_DRIVES,
        default=False,
        cli_on=("/printer",),
        rdp_on=(("redirectprinters", "i:1"),),
        rdp_off=(("redirectprinters", "i:0"),),
    ),
    # ----------------------------------------------------------- дополнительно
    Option(
        key="cert",
        label="Проверка сертификата",
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="tofu",
        cli=("/cert:{value}",),
        choices=(
            ("tofu", "Запомнить при первом подключении (рекомендуется)"),
            ("deny", "Отклонять неизвестные"),
            ("ignore", "Не проверять (небезопасно)"),
        ),
        hint="«Не проверять» отключает защиту от MITM.",
    ),
    Option(
        key="network",
        label="Профиль сети",
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="auto",
        cli=("/network:{value}",),
        choices=(
            ("auto", "Автоматически"),
            ("lan", "Локальная сеть"),
            ("wan", "WAN"),
            ("broadband-high", "Широкополосный (высокий)"),
            ("broadband-low", "Широкополосный (низкий)"),
            ("modem", "Модем"),
        ),
    ),
    Option(
        key="gfx",
        label="Графический конвейер (GFX)",
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="",
        unset="",
        cli=("/gfx:{value}",),
        choices=(
            ("", "По умолчанию"),
            ("RFX", "RemoteFX"),
            ("AVC444", "H.264 (AVC444)"),
        ),
        hint="Если чёрное окно — выберите «Выключить» (баг FreeRDP 3.31.x).",
    ),
    Option(
        key="gfx_off",
        label="Выключить GFX совсем",
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-gfx",),
        hint="Обход чёрного окна на FreeRDP 3.31.x (баг #13348).",
    ),
    Option(
        key="kbd_layout",
        label="Раскладка клавиатуры",
        group=GROUP_ADVANCED,
        kind=KIND_CHOICE,
        default="",
        unset="",
        cli=("/kbd:layout:{value}",),
        choices=(
            ("", "Как на сервере"),
            ("0x00000409", "Английская (US)"),
            ("0x00000419", "Русская"),
            ("0x00000422", "Украинская"),
            ("0x00000407", "Немецкая"),
            ("0x0000040c", "Французская"),
        ),
    ),
    Option(
        key="compression",
        label="Сжатие",
        group=GROUP_ADVANCED,
        default=True,
        cli_on=("+compression",),
        cli_off=("-compression",),
        rdp_on=(("compression", "i:1"),),
        rdp_off=(("compression", "i:0"),),
    ),
    Option(
        key="disable_wallpaper",
        label="Отключить обои",
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-wallpaper",),
        rdp_on=(("disable wallpaper", "i:1"),),
        rdp_off=(("disable wallpaper", "i:0"),),
    ),
    Option(
        key="disable_themes",
        label="Отключить темы",
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-themes",),
        rdp_on=(("disable themes", "i:1"),),
        rdp_off=(("disable themes", "i:0"),),
    ),
    Option(
        key="disable_menu_anims",
        label="Отключить анимацию меню",
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-menu-anims",),
        rdp_on=(("disable menu anims", "i:1"),),
        rdp_off=(("disable menu anims", "i:0"),),
    ),
    Option(
        key="disable_fonts",
        label="Отключить сглаживание шрифтов",
        group=GROUP_ADVANCED,
        default=False,
        cli_on=("-fonts",),
        # полярность обратная: «отключить сглаживание» = allow font smoothing:0
        rdp_on=(("allow font smoothing", "i:0"),),
        rdp_off=(("allow font smoothing", "i:1"),),
    ),
    Option(
        key="auto_reconnect",
        label="Переподключаться при обрыве",
        group=GROUP_ADVANCED,
        default=True,
        cli_on=("+auto-reconnect",),
        cli_off=("-auto-reconnect",),
    ),
    Option(
        key="auto_reconnect_retries",
        label="Попыток переподключения",
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
        width, _, height = size.partition("x")
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
