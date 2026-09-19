"""Поиск клиента FreeRDP, сборка командной строки и запуск.

Здесь нет ни одной строки работы с GTK: модуль чистый и тестируемый.
Лаунчер намеренно НЕ линкуется с libfreerdp и не рисует RDP сам — он запускает
официальный клиент отдельным процессом. Именно поэтому он не наследует класс
багов GUI-обёрток (см. README проекта).
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from . import options as opts
from .model import Profile


@dataclass(frozen=True)
class ClientSpec:
    binary: str
    title: str
    deprecated: bool = False
    note: str = ""


#: Порядок = приоритет выбора.
CLIENTS: tuple[ClientSpec, ...] = (
    ClientSpec("sdl-freerdp", "SDL3 (рекомендуется)"),
    ClientSpec(
        "xfreerdp",
        "X11 / XWayland",
        note="На Wayland идёт через XWayland: возможны мыло и неверный масштаб.",
    ),
    ClientSpec(
        "wlfreerdp",
        "Wayland (устарел)",
        deprecated=True,
        note="Официально объявлен заброшенным и будет удалён из дистрибутивов.",
    ),
)


def discover_clients() -> list[tuple[ClientSpec, str]]:
    """Найденные клиенты в порядке приоритета: [(описание, полный путь)]."""
    found: list[tuple[ClientSpec, str]] = []
    for spec in CLIENTS:
        path = shutil.which(spec.binary)
        if path:
            found.append((spec, path))
    return found


def default_client() -> tuple[ClientSpec, str] | None:
    clients = discover_clients()
    return clients[0] if clients else None


def build_argv(profile: Profile, client_path: str, password: str | None = None) -> list[str]:
    """Полная командная строка. Пароль в неё НЕ попадает (передаётся через stdin)."""
    if not profile.host:
        raise ValueError("не задан адрес хоста")

    argv = [client_path, f"/v:{profile.address}"]
    if profile.username:
        argv.append(f"/u:{profile.username}")
    if profile.domain:
        argv.append(f"/d:{profile.domain}")
    argv.extend(opts.cli_arguments(profile.values))
    if password:
        argv.append("/from-stdin")
    return argv


def spawn(profile: Profile, client_path: str, password: str | None = None) -> subprocess.Popen:
    """Запускает клиент. Пароль уходит через stdin — его не видно в списке процессов."""
    argv = build_argv(profile, client_path, password)
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE if password else subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if password and process.stdin is not None:
        try:
            process.stdin.write((password + "\n").encode("utf-8"))
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass
    return process


def clients_report() -> str:
    """Человекочитаемая сводка о найденных клиентах (для окна «О программе»)."""
    found = discover_clients()
    if not found:
        return "Клиент FreeRDP не найден. Установите пакет freerdp."
    lines = []
    for spec, path in found:
        mark = " (устарел)" if spec.deprecated else ""
        lines.append(f"{spec.binary}{mark}: {path}")
    return "\n".join(lines)
