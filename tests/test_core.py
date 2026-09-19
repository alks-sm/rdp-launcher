"""Тесты логики лаунчера (без GTK: запускаются где угодно)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdp_launcher import launcher, options as opts, rdpfile          # noqa: E402
from rdp_launcher.model import Profile                                 # noqa: E402
from rdp_launcher.storage import ProfileStore                          # noqa: E402


def sample_profile() -> Profile:
    return Profile(
        name="Рабочий",
        host="rdp.example.com",
        username="user",
        domain="WORK",
        values={
            "fullscreen": False,
            "multimon": True,
            "audio_mode": "redirect",
            "microphone": True,
            "clipboard": True,
            "drives": [("home", "/home/user")],
            "cert": "tofu",
            "auto_reconnect": True,
            "gfx_off": True,
            "size": "1920x1080",
        },
    )


class TestRegistry(unittest.TestCase):
    def test_every_option_has_ui_metadata(self) -> None:
        for opt in opts.OPTIONS:
            with self.subTest(option=opt.key):
                self.assertTrue(opt.label, "у опции нет подписи")
                self.assertIn(opt.group, dict(opts.GROUPS))
                if opt.kind == opts.KIND_CHOICE:
                    self.assertTrue(opt.choices, "у выбора нет вариантов")

    def test_keys_are_unique(self) -> None:
        keys = [o.key for o in opts.OPTIONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_defaults_cover_all_options(self) -> None:
        self.assertEqual(set(opts.defaults()), {o.key for o in opts.OPTIONS})

    def test_choices_contain_default(self) -> None:
        for opt in opts.OPTIONS:
            if opt.kind != opts.KIND_CHOICE:
                continue
            with self.subTest(option=opt.key):
                self.assertIn(opt.default, [value for value, _ in opt.choices])


class TestFlagsAcceptedByRealClient(unittest.TestCase):
    """Каждый флаг реестра проверяется на настоящем клиенте FreeRDP.

    Текстовый разбор справки ненадёжен: она использует нотацию `[-|/]clipboard`
    и не перечисляет все формы. Поэтому флаги проверяются эмпирически — клиент
    сообщает «Unexpected keyword», если аргумент не распознан.
    """

    BIN = shutil.which("sdl-freerdp") or shutil.which("xfreerdp")
    RUN_TIMEOUT = 20

    def _run(self, flags: list[str]) -> str:
        argv = [self.BIN, *flags, "/v:127.0.0.1:1", "/cert:ignore", "/timeout:500"]
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, timeout=self.RUN_TIMEOUT, check=False
            )
        except subprocess.TimeoutExpired as exc:
            return (exc.stdout or "") + (exc.stderr or "")
        return proc.stdout + proc.stderr

    def _concrete(self, template: str, opt: opts.Option) -> str:
        """Подставляет в шаблон осмысленное значение."""
        value = ""
        for candidate, _label in opt.choices:
            if candidate:
                value = candidate
                break
        if not value:
            value = opt.default if opt.default not in (None, "") else "1"
        return template.format(value=value, rdp_value=value)

    def test_every_registry_flag_is_accepted(self) -> None:
        if not self.BIN:
            self.skipTest("клиент FreeRDP не найден")
        failures: list[tuple[str, str]] = []
        for opt in opts.OPTIONS:
            forms: list[str] = []
            if opt.kind == opts.KIND_DRIVES:
                forms.append("/drive:tmp,/tmp")
            forms.extend(opt.cli_on)
            forms.extend(opt.cli_off)
            forms.extend(self._concrete(t, opt) for t in opt.cli)
            for form in forms:
                with self.subTest(option=opt.key, flag=form):
                    out = self._run([form])
                    if "Unexpected keyword" in out or "Failed at index" in out:
                        failures.append((opt.key, form))
        self.assertEqual(failures, [], f"клиент отверг флаги: {failures}")

    def test_control_bogus_flag_is_detected(self) -> None:
        """Проверка самого метода: заведомо мусорный флаг должен ловиться."""
        if not self.BIN:
            self.skipTest("клиент FreeRDP не найден")
        out = self._run(["/definitely-not-a-flag"])
        self.assertIn("Unexpected keyword", out)


class TestAudioComposite(unittest.TestCase):
    """Звук собирается из двух опций, отдельного флага качества не существует."""

    def test_redirect_adds_sound_backend(self) -> None:
        argv = launcher.build_argv(Profile(host="h", values={"audio_mode": "redirect"}), "sdl-freerdp")
        self.assertIn("/audio-mode:redirect", argv)
        self.assertIn("/sound:sys:pulse", argv)

    def test_quality_is_sound_suboption(self) -> None:
        argv = launcher.build_argv(
            Profile(host="h", values={"audio_mode": "redirect", "audio_quality": "high"}), "sdl-freerdp"
        )
        self.assertIn("/sound:sys:pulse,quality:high", argv)

    def test_latency_is_sound_suboption(self) -> None:
        argv = launcher.build_argv(
            Profile(host="h", values={"audio_mode": "redirect", "sound_latency": 100}), "sdl-freerdp"
        )
        self.assertIn("/sound:sys:pulse,latency:100", argv)

    def test_latency_and_quality_together_follow_help_order(self) -> None:
        argv = launcher.build_argv(
            Profile(host="h", values={"audio_mode": "redirect", "sound_latency": 80, "audio_quality": "high"}),
            "sdl-freerdp",
        )
        self.assertIn("/sound:sys:pulse,latency:80,quality:high", argv)

    def test_zero_latency_omitted(self) -> None:
        argv = launcher.build_argv(Profile(host="h", values={"sound_latency": 0}), "sdl-freerdp")
        self.assertIn("/sound:sys:pulse", argv)
        self.assertFalse([a for a in argv if "latency" in a])

    def test_server_mode_has_no_client_backend(self) -> None:
        argv = launcher.build_argv(Profile(host="h", values={"audio_mode": "server"}), "sdl-freerdp")
        self.assertIn("/audio-mode:server", argv)
        self.assertFalse([a for a in argv if a.startswith("/sound:")])

    def test_none_mode_disables_audio(self) -> None:
        argv = launcher.build_argv(Profile(host="h", values={"audio_mode": "none"}), "sdl-freerdp")
        self.assertIn("/audio-mode:none", argv)
        self.assertFalse([a for a in argv if a.startswith("/sound:")])


class TestArgv(unittest.TestCase):
    def test_argv_contains_expected_flags(self) -> None:
        argv = launcher.build_argv(sample_profile(), "/usr/bin/sdl-freerdp")
        self.assertEqual(argv[0], "/usr/bin/sdl-freerdp")
        self.assertIn("/v:rdp.example.com", argv)          # порт 3389 опущен
        self.assertIn("/u:user", argv)
        self.assertIn("/d:WORK", argv)
        self.assertIn("/multimon", argv)
        self.assertIn("/audio-mode:redirect", argv)
        self.assertIn("/microphone:sys:pulse", argv)
        self.assertIn("+clipboard", argv)
        self.assertIn("/drive:home,/home/user", argv)
        self.assertIn("/cert:tofu", argv)
        self.assertIn("+auto-reconnect", argv)
        self.assertIn("-gfx", argv)
        self.assertIn("/size:1920x1080", argv)

    def test_password_never_in_argv(self) -> None:
        argv = launcher.build_argv(sample_profile(), "sdl-freerdp", password="hunter2")
        self.assertNotIn("hunter2", " ".join(argv))
        self.assertIn("/from-stdin", argv)

    def test_no_stdin_flag_without_password(self) -> None:
        argv = launcher.build_argv(sample_profile(), "sdl-freerdp")
        self.assertNotIn("/from-stdin", argv)

    def test_unset_values_are_omitted(self) -> None:
        profile = Profile(host="h", values={"gfx": "", "audio_quality": "", "kbd_layout": ""})
        argv = launcher.build_argv(profile, "sdl-freerdp")
        self.assertFalse([a for a in argv if a.startswith("/gfx:")])
        self.assertFalse([a for a in argv if a.startswith("/audio-quality:")])
        self.assertFalse([a for a in argv if a.startswith("/kbd:layout:")])

    def test_nonstandard_port_included(self) -> None:
        profile = Profile(host="host", port=4444)
        self.assertIn("/v:host:4444", launcher.build_argv(profile, "sdl-freerdp"))

    def test_empty_host_rejected(self) -> None:
        with self.assertRaises(ValueError):
            launcher.build_argv(Profile(host=""), "sdl-freerdp")


class TestRdpFile(unittest.TestCase):
    def test_roundtrip_preserves_meaning(self) -> None:
        original = sample_profile()
        restored = rdpfile.parse_rdp_text(rdpfile.to_rdp_text(original))
        self.assertEqual(restored.host, original.host)
        self.assertEqual(restored.username, original.username)
        self.assertEqual(restored.domain, original.domain)
        self.assertEqual(restored.values["multimon"], True)
        self.assertEqual(restored.values["audio_mode"], "redirect")
        self.assertEqual(restored.values["microphone"], True)
        self.assertEqual(restored.values["clipboard"], True)
        self.assertEqual(restored.values["size"], "1920x1080")
        self.assertEqual(restored.values["disable_fonts"], False)

    def test_fullscreen_maps_to_screen_mode(self) -> None:
        profile = Profile(host="h", values={"fullscreen": True})
        text = rdpfile.to_rdp_text(profile)
        self.assertIn("screen mode id:i:2", text)

    def test_fonts_polarity(self) -> None:
        profile = Profile(host="h", values={"disable_fonts": True})
        self.assertIn("allow font smoothing:i:0", rdpfile.to_rdp_text(profile))
        back = rdpfile.parse_rdp_text(rdpfile.to_rdp_text(profile))
        self.assertTrue(back.values["disable_fonts"])

    def test_drives_export(self) -> None:
        profile = Profile(host="h", values={"drives": [("home", "/home/x")]})
        self.assertIn("drivestoredirect:s:*", rdpfile.to_rdp_text(profile))

    def test_comments_and_type_prefixes_parsed(self) -> None:
        text = "; comment\nfull address:s:1.2.3.4:4444\nusername:s:bob\nuse multimon:i:1\n"
        profile = rdpfile.parse_rdp_text(text)
        self.assertEqual(profile.host, "1.2.3.4")
        self.assertEqual(profile.port, 4444)
        self.assertEqual(profile.username, "bob")
        self.assertTrue(profile.values["multimon"])


class TestNormalize(unittest.TestCase):
    def test_drives_accept_dicts_tuples_and_junk(self) -> None:
        values = opts.normalize({
            "drives": [{"name": "a", "path": "/a"}, ("b", "/b"), ["c", "/c"], ("d", ""), "junk"],
        })
        self.assertEqual(values["drives"], (("a", "/a"), ("b", "/b"), ("c", "/c")))

    def test_bad_int_falls_back_to_default(self) -> None:
        self.assertEqual(opts.normalize({"auto_reconnect_retries": "abc"})["auto_reconnect_retries"], 20)

    def test_unknown_keys_ignored(self) -> None:
        self.assertNotIn("nonsense", opts.normalize({"nonsense": 1}))


class TestStorage(unittest.TestCase):
    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProfileStore(Path(tmp))
            profile = sample_profile()
            store.add(profile)
            self.assertTrue((Path(tmp) / "profiles.json").exists())

            reloaded = ProfileStore(Path(tmp)).load()
            self.assertEqual(len(reloaded), 1)
            self.assertEqual(reloaded[0].id, profile.id)
            self.assertEqual(reloaded[0].values["drives"], (("home", "/home/user"),))

    def test_no_secrets_in_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProfileStore(Path(tmp))
            store.add(sample_profile())
            raw = (Path(tmp) / "profiles.json").read_text(encoding="utf-8")
            self.assertNotIn("password", raw.lower())
            json.loads(raw)  # файл остаётся валидным JSON

    def test_corrupt_file_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "profiles.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(ProfileStore(Path(tmp)).load(), [])

    def test_upsert_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProfileStore(Path(tmp))
            profile = sample_profile()
            store.upsert(profile)
            profile.name = "Переименованный"
            store.upsert(profile)
            self.assertEqual(len(store.profiles), 1)
            self.assertEqual(store.profiles[0].name, "Переименованный")
            store.remove(profile.id)
            self.assertEqual(store.profiles, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
