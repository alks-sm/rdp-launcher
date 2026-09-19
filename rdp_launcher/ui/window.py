"""Главное окно: список профилей и подключение."""
from __future__ import annotations

import threading
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from .. import launcher, rdpfile
from ..launcher import ClientSpec
from ..model import Profile
from ..secrets import SecretStore
from ..storage import ProfileStore
from .profile_dialog import ProfileDialog
from ..i18n import _


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        application: Adw.Application,
        store: ProfileStore,
        secrets: SecretStore,
    ) -> None:
        super().__init__(application=application, title="RDP Launcher", default_width=560, default_height=680)
        self.store = store
        self.secrets = secrets
        self._clients = launcher.discover_clients()
        self._client: tuple[ClientSpec, str] | None = self._clients[0] if self._clients else None

        for name in ("edit", "duplicate", "export", "delete"):
            action = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            action.connect("activate", getattr(self, f"_action_{name}"))
            self.add_action(action)

        self._toasts = Adw.ToastOverlay()
        self._page = Adw.PreferencesPage()
        self._group = Adw.PreferencesGroup(title=_("Connections"))
        self._rows: list[Gtk.Widget] = []
        self._page.add(self._group)

        self._empty = Adw.StatusPage(
            icon_name="network-server-symbolic",
            title=_("No connections yet"),
            description=_("Create a profile and the launcher will start the official FreeRDP client."),
        )
        add_button = Gtk.Button(label=_("Create a connection"))
        add_button.add_css_class("suggested-action")
        add_button.add_css_class("pill")
        add_button.set_halign(Gtk.Align.CENTER)
        add_button.connect("clicked", lambda *_: self._new_profile())
        self._empty.set_child(add_button)

        self._stack = Gtk.Stack()
        self._stack.add_named(self._empty, "empty")
        self._stack.add_named(self._page, "list")
        self._toasts.set_child(self._stack)

        self._banner = Adw.Banner(revealed=False)

        header = Adw.HeaderBar()
        new_button = Gtk.Button(icon_name="list-add-symbolic")
        new_button.set_tooltip_text(_("New connection"))
        new_button.connect("clicked", lambda *_: self._new_profile())
        header.pack_start(new_button)

        menu = Gio.Menu()
        menu.append(_("Import from .rdp…"), "win.import")
        menu.append(_("About"), "win.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_button)

        for name, handler in (("import", self._import_rdp), ("about", self._about)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.add_top_bar(self._banner)
        toolbar.set_content(self._toasts)
        self.set_content(toolbar)

        self._check_clients()
        self.refresh()

    # ------------------------------------------------------------------ клиент
    def _check_clients(self) -> None:
        if not self._clients:
            self._banner.set_title(_("FreeRDP client not found. Install the freerdp package."))
            self._banner.set_revealed(True)
            return
        spec, path = self._clients[0]
        if spec.deprecated:
            self._banner.set_title(
                _("Only a deprecated client was found: {binary}. Install the freerdp package and use sdl-freerdp.").format(
                    binary=spec.binary
                )
            )
            self._banner.set_revealed(True)
        self._banner.set_tooltip_text(launcher.clients_report())

    # ------------------------------------------------------------------- список
    def refresh(self) -> None:
        # Строки запоминаем сами: Adw.PreferencesGroup оборачивает их во внутренний
        # контейнер, поэтому обход через get_first_child()/remove() не работает.
        for row in self._rows:
            self._group.remove(row)
        self._rows.clear()

        profiles = self.store.profiles
        self._stack.set_visible_child_name("list" if profiles else "empty")
        for profile in profiles:
            row = self._profile_row(profile)
            self._rows.append(row)
            self._group.add(row)

    def _profile_row(self, profile: Profile) -> Adw.ActionRow:
        row = Adw.ActionRow(title=profile.name, subtitle=self._subtitle(profile))
        row.set_activatable(True)
        row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        row.connect("activated", lambda *_: self._connect(profile))

        connect = Gtk.Button(icon_name="media-playback-start-symbolic", valign=Gtk.Align.CENTER)
        connect.add_css_class("flat")
        connect.set_tooltip_text(_("Connect"))
        connect.connect("clicked", lambda *_: self._connect(profile))
        row.add_suffix(connect)

        menu = Gio.Menu()
        menu.append(_("Edit"), f"win.edit::{profile.id}")
        menu.append(_("Duplicate"), f"win.duplicate::{profile.id}")
        menu.append(_("Export to .rdp"), f"win.export::{profile.id}")
        menu.append(_("Delete"), f"win.delete::{profile.id}")
        menu_button = Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=menu)
        menu_button.add_css_class("flat")
        row.add_suffix(menu_button)
        return row

    def _subtitle(self, profile: Profile) -> str:
        if not profile.host:
            return _("address not set")
        parts = [profile.login + "@" + profile.address if profile.login else profile.address]
        values = profile.values
        if values.get("fullscreen"):
            parts.append(_("full screen"))
        if values.get("multimon"):
            parts.append(_("all monitors"))
        audio = values.get("audio_mode")
        parts.append({"redirect": _("audio here"), "server": _("audio on server"), "none": _("no audio")}.get(audio, ""))
        drives = values.get("drives") or ()
        if drives:
            parts.append(_("drives: {count}").format(count=len(drives)))
        return " · ".join(p for p in parts if p)

    # -------------------------------------------------------------- подключение
    def _connect(self, profile: Profile) -> None:
        if self._client is None:
            self._toast(_("FreeRDP client not found"))
            return
        spec, path = self._client
        password = self.secrets.lookup(profile.id)
        try:
            process = launcher.spawn(profile, path, password)
        except Exception as exc:  # noqa: BLE001 — показываем пользователю любую ошибку запуска
            self._toast(_("Failed to start {binary}: {error}").format(binary=spec.binary, error=exc))
            return
        self._toast(_("Started: {name} ({binary})").format(name=profile.name, binary=spec.binary))
        threading.Thread(target=self._watch, args=(process, profile.name), daemon=True).start()

    def _watch(self, process: Any, name: str) -> None:
        code = process.wait()
        GLib.idle_add(
            self._toast,
            _("Session \u201c{name}\u201d finished (exit code {code})").format(name=name, code=code),
        )

    def _toast(self, message: str) -> bool:
        self._toasts.add_toast(Adw.Toast(title=message))
        return False

    # ----------------------------------------------------------------- действия
    def _find(self, param: GLib.Variant) -> Profile | None:
        return self.store.find(param.get_string())

    def _action_edit(self, _action: Gio.SimpleAction, param: GLib.Variant) -> None:
        profile = self._find(param)
        if profile is not None:
            self._edit_profile(profile)

    def _action_duplicate(self, _action: Gio.SimpleAction, param: GLib.Variant) -> None:
        profile = self._find(param)
        if profile is not None:
            self.store.add(profile.copy())
            self.refresh()

    def _action_delete(self, _action: Gio.SimpleAction, param: GLib.Variant) -> None:
        profile = self._find(param)
        if profile is None:
            return
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Delete this connection?"),
            body=_("Profile \u201c{name}\u201d will be deleted together with its saved password.").format(
                name=profile.name
            ),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response == "delete":
                self.secrets.clear(profile.id)
                self.store.remove(profile.id)
                self.refresh()

        dialog.connect("response", on_response)
        dialog.present()

    def _action_export(self, _action: Gio.SimpleAction, param: GLib.Variant) -> None:
        profile = self._find(param)
        if profile is None:
            return
        dialog = Gtk.FileDialog(title=_("Export to .rdp"), initial_name=f"{profile.name}.rdp")

        def done(source: Gtk.FileDialog, result: Any) -> None:
            try:
                target = source.save_finish(result)
            except Exception:
                return
            if target is None:
                return
            path = target.get_path()
            if not path:
                return
            if not path.endswith(".rdp"):
                path += ".rdp"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(rdpfile.to_rdp_text(profile))
            self._toast(_("Saved: {path}").format(path=path))

        dialog.save(parent=self, callback=done)

    def _import_rdp(self, *_args: Any) -> None:
        dialog = Gtk.FileDialog(title=_("Import .rdp"))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("RDP files"))
        file_filter.add_pattern("*.rdp")
        filters.append(file_filter)
        dialog.set_filters(filters)

        def done(source: Gtk.FileDialog, result: Any) -> None:
            try:
                target = source.open_finish(result)
            except Exception:
                return
            if target is None or not target.get_path():
                return
            try:
                text = open(target.get_path(), encoding="utf-8", errors="replace").read()
                profile = rdpfile.parse_rdp_text(text)
            except OSError as exc:
                self._toast(_("Could not read the file: {error}").format(error=exc))
                return
            self.store.add(profile)
            self.refresh()
            self._toast(_("Imported: {name}").format(name=profile.name))

        dialog.open(parent=self, callback=done)

    def _about(self, *_args: Any) -> None:
        dialog = Adw.AboutDialog(
            application_name="RDP Launcher",
            application_icon="io.github.rdplauncher.RdpLauncher",
            version="0.1.0",
            comments=_(
                "A minimal front-end for the official FreeRDP client.\n"
                "The launcher does not render RDP itself: it starts sdl-freerdp as a separate process."
            ),
            developers=["alks-sm"],
        )
        dialog.set_debug_info(launcher.clients_report())
        dialog.present(self)

    # -------------------------------------------------------------- профили
    def _new_profile(self) -> None:
        profile = Profile(name=_("New connection"), host="")
        self._edit_profile(profile, is_new=True)

    def _edit_profile(self, profile: Profile, is_new: bool = False) -> None:
        has_password = bool(self.secrets.lookup(profile.id))

        def on_save(updated: Profile, typed_password: str | None, remember: bool) -> None:
            if typed_password:
                self.secrets.store(updated.id, typed_password)
            elif not remember:
                self.secrets.clear(updated.id)
            if is_new:
                self.store.add(updated)
            else:
                self.store.upsert(updated)
            self.refresh()

        dialog = ProfileDialog(profile, has_password, on_save)
        dialog.present(self)
