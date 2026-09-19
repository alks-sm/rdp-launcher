"""Пароли в связке ключей GNOME (libsecret).

В файле профиля секретов нет. Если связка ключей недоступна, пароль можно
вводить каждый раз — лаунчер просто не сохранит его.
"""
from __future__ import annotations

import gi

gi.require_version("Secret", "1")
from gi.repository import Secret  # noqa: E402

SCHEMA = Secret.Schema.new(
    "io.github.rdplauncher.RdpLauncher",
    Secret.SchemaFlags.NONE,
    {"profile": Secret.SchemaAttributeType.STRING},
)


class SecretStore:
    def __init__(self) -> None:
        self.available = True
        self._memory: dict[str, str] = {}

    def lookup(self, profile_id: str) -> str | None:
        try:
            return Secret.password_lookup_sync(SCHEMA, {"profile": profile_id}, None)
        except Exception:  # связка ключей недоступна / отменена
            self.available = False
            return self._memory.get(profile_id)

    def store(self, profile_id: str, password: str) -> bool:
        self._memory[profile_id] = password
        try:
            return bool(
                Secret.password_store_sync(
                    SCHEMA,
                    {"profile": profile_id},
                    Secret.COLLECTION_DEFAULT,
                    f"RDP: {profile_id}",
                    password,
                    None,
                )
            )
        except Exception:
            self.available = False
            return False

    def clear(self, profile_id: str) -> None:
        self._memory.pop(profile_id, None)
        try:
            Secret.password_clear_sync(SCHEMA, {"profile": profile_id}, None)
        except Exception:
            self.available = False
