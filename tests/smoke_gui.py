"""Дымовой тест интерфейса: собирает окно и диалог настроек, имитирует сохранение.

Требует графической сессии. Если дисплея нет — тест пропускается, а не падает.
Запуск: python3 tests/smoke_gui.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from rdp_launcher import launcher, options as opts  # noqa: E402
from rdp_launcher.model import Profile  # noqa: E402
from rdp_launcher.secrets import SecretStore  # noqa: E402
from rdp_launcher.storage import ProfileStore  # noqa: E402
from rdp_launcher.ui.profile_dialog import ProfileDialog  # noqa: E402
from rdp_launcher.ui.window import MainWindow  # noqa: E402

captured: dict[str, object] = {}


class SmokeApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="io.github.rdplauncher.Smoke")
        self.failures: list[str] = []
        self.saved: tuple[Profile, str | None, bool] | None = None

    def do_activate(self) -> None:
        import tempfile

        tmp = tempfile.mkdtemp()
        store = ProfileStore(Path(tmp))
        store.add(
            Profile(
                name="Тест",
                host="rdp.example.com",
                username="user",
                domain="WORK",
                values={"multimon": True, "drives": [("home", "/home/user")], "audio_quality": "high"},
            )
        )
        window = MainWindow(application=self, store=store, secrets=SecretStore())
        window.present()
        captured["window"] = "ok"
        captured["rows"] = len(window._rows)
        captured["subtitle"] = window._subtitle(store.profiles[0])

        # Каждый пункт реестра должен создать строку без исключения.
        profile = store.profiles[0]

        def on_save(updated: Profile, password: str | None, remember: bool) -> None:
            self.saved = (updated, password, remember)

        dialog = ProfileDialog(profile, has_stored_password=False, on_save=on_save)
        try:
            dialog.present(window)
            captured["dialog"] = "ok"
            captured["getters"] = sorted(dialog._getters)
            dialog._save()  # имитируем нажатие «Сохранить»
        except Exception as exc:  # noqa: BLE001
            self.failures.append(f"dialog: {exc!r}")
        captured["saved"] = self.saved[0].values if self.saved else None
        captured["saved_password"] = self.saved[1] if self.saved else None
        GLib.timeout_add(300, self.quit)


def main() -> int:
    app = SmokeApp()
    try:
        code = app.run([])
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP: нет графической сессии ({exc})")
        return 0

    expected_keys = {opt.key for opt in opts.OPTIONS}
    got = set(captured.get("getters") or [])
    missing = expected_keys - got
    problems = list(app.failures)
    if missing:
        problems.append(f"в диалоге нет полей для опций: {sorted(missing)}")
    if captured.get("window") != "ok":
        problems.append("окно не построено")
    if captured.get("dialog") != "ok":
        problems.append("диалог не построен")
    if captured.get("saved") is None:
        problems.append("сохранение не сработало")
    else:
        values = captured["saved"]
        assert isinstance(values, dict)
        if values.get("audio_quality") != "high":
            problems.append(f"качество звука не сохранилось: {values.get('audio_quality')!r}")
        if tuple(values.get("drives") or ()) != (("home", "/home/user"),):
            problems.append(f"диски не сохранились: {values.get('drives')!r}")
        if values.get("multimon") is not True:
            problems.append("multimon не сохранился")

    print("--- результат ---")
    for key, value in captured.items():
        print(f"  {key}: {value}")
    if problems:
        print("ПРОБЛЕМЫ:")
        for problem in problems:
            print(f"  ! {problem}")
        return 1
    print("SMOKE OK")
    return code


if __name__ == "__main__":
    sys.exit(main())
