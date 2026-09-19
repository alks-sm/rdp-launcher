"""Генерация скриншотов интерфейса без участия человека.

Строит главное окно и диалог настроек с демонстрационным профилем и сохраняет
их в PNG через GdkTexture. Запускать там, где есть графическая сессия:

    GSK_RENDERER=cairo python3 tools/make-screenshots.py

Требуется только для документации: обычной работе приложения не нужно.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from rdp_launcher.model import Profile  # noqa: E402
from rdp_launcher.secrets import SecretStore  # noqa: E402
from rdp_launcher.storage import ProfileStore  # noqa: E402
from rdp_launcher.ui.profile_dialog import ProfileDialog  # noqa: E402
from rdp_launcher.ui.window import MainWindow  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def snapshot(widget: Gtk.Widget, path: Path) -> bool:
    """Рендерит виджет в PNG. Возвращает True при успехе."""
    try:
        paintable = Gtk.WidgetPaintable.new(widget)
        width = widget.get_width()
        height = widget.get_height()
        native = widget.get_native()
        if native is None or width <= 1 or height <= 1:
            print(f"  {path.name}: виджет ещё не отрисован ({width}x{height})")
            return False
        snapshot_ = Gtk.Snapshot.new()
        paintable.snapshot(snapshot_, width, height)
        node = snapshot_.to_node()
        renderer = native.get_renderer()
        texture = renderer.render_texture(node, None)
        texture.save_to_png(str(path))
        print(f"  {path.name}: {width}x{height}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  {path.name}: ошибка {exc!r}")
        return False


class ShotApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="io.github.rdplauncher.Screenshots")
        self.ok = 0

    def do_activate(self) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        store = ProfileStore(Path(tempfile.mkdtemp()))
        store.add(
            Profile(
                name="Workstation",
                host="rdp.example.com",
                username="user",
                domain="WORK",
                values={"multimon": False, "audio_mode": "redirect", "sound_latency": 100,
                        "drives": (("home", "/home/user"),), "size": "1920x1080"},
            )
        )
        store.add(Profile(name="Test server", host="192.0.2.10", port=4444, username="administrator"))

        window = MainWindow(application=self, store=store, secrets=SecretStore())
        window.set_default_size(560, 680)
        window.present()

        def capture_window() -> bool:
            if snapshot(window, OUT / "main-window.png"):
                self.ok += 1
            dialog = ProfileDialog(store.profiles[0], False, lambda *_: None, parent=window)
            dialog.set_content_width(560)
            dialog.set_content_height(720)
            dialog.present(window)

            def capture_dialog() -> bool:
                child = dialog.get_child()
                if child is not None and snapshot(child, OUT / "profile-dialog.png"):
                    self.ok += 1
                GLib.timeout_add(200, self.quit)
                return False

            GLib.timeout_add(1200, capture_dialog)
            return False

        GLib.timeout_add(1500, capture_window)


def main() -> int:
    app = ShotApp()
    try:
        app.run([])
    except Exception as exc:  # noqa: BLE001
        print(f"нет графической сессии: {exc}")
        return 1
    print(f"готово, сохранено файлов: {app.ok}")
    return 0 if app.ok else 1


if __name__ == "__main__":
    sys.exit(main())
