"""Хранилище профилей: обычный JSON в каталоге конфигурации."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .model import Profile

APP_ID = "rdp-launcher"
ENV_CONFIG_DIR = "RDP_LAUNCHER_CONFIG_DIR"


def config_dir() -> Path:
    """Каталог конфигурации. Переопределяется переменной окружения (удобно для тестов)."""
    override = os.environ.get(ENV_CONFIG_DIR)
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / APP_ID


class ProfileStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or config_dir()
        self.path = self.directory / "profiles.json"
        self.profiles: list[Profile] = []

    def load(self) -> list[Profile]:
        if not self.path.exists():
            self.profiles = []
            return self.profiles
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.profiles = []
            return self.profiles
        items = data.get("profiles") if isinstance(data, dict) else data
        self.profiles = [Profile.from_dict(item) for item in (items or [])]
        return self.profiles

    def save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "profiles": [p.to_dict() for p in self.profiles]}
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, profile: Profile) -> None:
        self.profiles.append(profile)
        self.save()

    def upsert(self, profile: Profile) -> None:
        for index, existing in enumerate(self.profiles):
            if existing.id == profile.id:
                self.profiles[index] = profile
                break
        else:
            self.profiles.append(profile)
        self.save()

    def remove(self, profile_id: str) -> None:
        self.profiles = [p for p in self.profiles if p.id != profile_id]
        self.save()

    def find(self, profile_id: str) -> Profile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)
