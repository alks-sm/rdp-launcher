"""Модель профиля подключения."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from . import options as opts

DEFAULT_PORT = 3389


@dataclass
class Profile:
    name: str = "Новое подключение"
    host: str = ""
    port: int = DEFAULT_PORT
    username: str = ""
    domain: str = ""
    values: dict[str, Any] = field(default_factory=opts.defaults)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        self.values = opts.normalize(self.values)

    @property
    def address(self) -> str:
        """Адрес для FreeRDP: порт опускается, если он стандартный."""
        if not self.host:
            return ""
        if self.port and self.port != DEFAULT_PORT:
            return f"{self.host}:{self.port}"
        return self.host

    @property
    def login(self) -> str:
        if self.domain and self.username:
            return f"{self.domain}\\{self.username}"
        return self.username

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "domain": self.domain,
            "values": {
                key: (list(value) if isinstance(value, tuple) else value)
                for key, value in self.values.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        port = data.get("port", DEFAULT_PORT)
        try:
            port = int(port)
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        return cls(
            name=str(data.get("name") or "Новое подключение"),
            host=str(data.get("host") or ""),
            port=port,
            username=str(data.get("username") or ""),
            domain=str(data.get("domain") or ""),
            values=opts.normalize(data.get("values") or {}),
            id=str(data.get("id") or uuid.uuid4().hex),
        )

    def copy(self) -> "Profile":
        clone = Profile.from_dict(self.to_dict())
        clone.id = uuid.uuid4().hex
        return clone
