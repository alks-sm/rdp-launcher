"""Приложение RDP Launcher."""
from __future__ import annotations

import sys
from typing import Any

import gi

gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from . import APP_ID, APP_NAME, rdpfile
from .secrets import SecretStore
from .storage import ProfileStore
from .ui.window import MainWindow


class RdpLauncherApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        GLib.set_application_name(APP_NAME)
        self.store = ProfileStore()
        self.secrets = SecretStore()
        self.window: MainWindow | None = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self.store.load()

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(application=self, store=self.store, secrets=self.secrets)
        self.window.present()

    def do_open(self, files: list[Gio.File], n_files: int, _hint: str) -> None:
        """Открытие .rdp-файлов (в том числе через ярлык в файловом менеджере)."""
        self.do_activate()
        assert self.window is not None
        for gfile in files[:n_files]:
            path = gfile.get_path()
            if not path:
                continue
            try:
                profile = rdpfile.parse_rdp_text(open(path, encoding="utf-8", errors="replace").read())
            except OSError:
                continue
            self.store.add(profile)
        self.window.refresh()


def main(argv: list[str] | None = None) -> int:
    app = RdpLauncherApp()
    return app.run(argv if argv is not None else sys.argv)
