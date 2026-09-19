"""Диалог редактирования профиля.

Форма целиком строится из реестра опций (options.py): чтобы добавить настройку,
достаточно дописать одну запись в реестр — здесь менять ничего не нужно.
"""
from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk

from .. import options as opts
from ..model import Profile, DEFAULT_PORT
from ..i18n import _


class ProfileDialog(Adw.Dialog):
    def __init__(
        self,
        profile: Profile,
        has_stored_password: bool,
        on_save: Callable[[Profile, str | None, bool], None],
        parent: Gtk.Widget | None = None,
    ) -> None:
        super().__init__()
        self.set_title(profile.name or _("Connection"))
        self.set_content_width(560)
        self.set_content_height(720)

        self._profile = profile
        self._on_save = on_save
        self._has_stored_password = has_stored_password
        self._getters: dict[str, Callable[[], Any]] = {}

        page = Adw.PreferencesPage()
        page.add(self._basic_group(profile))
        for group_id, group_title in opts.GROUPS:
            group = Adw.PreferencesGroup(title=group_title)
            self._fill_group(group, group_id)
            page.add(group)

        header = Adw.HeaderBar()
        cancel = Gtk.Button(label=_("Cancel"))
        cancel.connect("clicked", lambda *_: self.close())
        save = Gtk.Button(label=_("Save"))
        save.add_css_class("suggested-action")
        save.connect("clicked", self._save)
        header.pack_start(cancel)
        header.pack_end(save)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(page)
        self.set_child(toolbar)

    # ------------------------------------------------------------- построение
    def _basic_group(self, profile: Profile) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("General"),
            description=_("Address and credentials. The password is kept in the GNOME keyring."),
        )

        self._name = Adw.EntryRow(title=_("Name"))
        self._name.set_text(profile.name)
        group.add(self._name)

        self._host = Adw.EntryRow(title=_("Address (host or IP)"))
        self._host.set_text(profile.host)
        group.add(self._host)

        self._port = Adw.SpinRow.new_with_range(1, 65535, 1)
        self._port.set_title(_("Port"))
        self._port.set_value(profile.port or DEFAULT_PORT)
        group.add(self._port)

        self._username = Adw.EntryRow(title=_("User name"))
        self._username.set_text(profile.username)
        group.add(self._username)

        self._domain = Adw.EntryRow(title=_("Domain"))
        self._domain.set_text(profile.domain)
        group.add(self._domain)

        self._password = Adw.PasswordEntryRow(title=_("Password"))
        self._password.set_show_apply_button(False)
        if self._has_stored_password:
            self._password.set_tooltip_text(_("A password is already saved — leave this field empty"))
        group.add(self._password)

        self._remember = Adw.SwitchRow(
            title=_("Keep the password in the keyring"),
            subtitle=_("If disabled, the client asks for the password itself"),
        )
        self._remember.set_active(self._has_stored_password)
        group.add(self._remember)

        self._import_hint = Adw.ActionRow(
            title=_("Hint"),
            subtitle=_("Leave the password empty and the client will ask when connecting."),
        )
        self._import_hint.set_activatable(False)
        group.add(self._import_hint)
        return group

    def _fill_group(self, group: Adw.PreferencesGroup, group_id: str) -> None:
        for opt in opts.options_in(group_id):
            if opt.kind == opts.KIND_DRIVES:
                group.add(self._drives_expander(opt))
                continue
            row = self._make_row(opt)
            if row is not None:
                group.add(row)

    def _make_row(self, opt: opts.Option) -> Gtk.Widget | None:
        value = self._profile.values.get(opt.key, opt.default)

        if opt.kind == opts.KIND_BOOL:
            row = Adw.SwitchRow(title=opt.label)
            row.set_active(bool(value))
            if opt.hint:
                row.set_subtitle(opt.hint)
            self._getters[opt.key] = row.get_active
            return row

        if opt.kind == opts.KIND_CHOICE:
            labels = [label for _value, label in opt.choices]
            values = [choice for choice, _label in opt.choices]
            row = Adw.ComboRow(title=opt.label)
            row.set_model(Gtk.StringList.new(labels))
            try:
                row.set_selected(values.index(value))
            except ValueError:
                row.set_selected(0)
            if opt.hint:
                row.set_subtitle(opt.hint)
            self._getters[opt.key] = lambda r=row, v=values: v[r.get_selected()]
            return row

        if opt.kind == opts.KIND_INT:
            row = Adw.SpinRow.new_with_range(0, 10_000, 1)
            row.set_title(opt.label)
            row.set_value(int(value if value is not None else opt.default or 0))
            if opt.hint:
                row.set_subtitle(opt.hint)
            self._getters[opt.key] = lambda r=row: int(r.get_value())
            return row

        if opt.kind == opts.KIND_TEXT:
            row = Adw.EntryRow(title=opt.label)
            row.set_text(str(value or ""))
            if opt.hint:
                row.set_tooltip_text(opt.hint)
            self._getters[opt.key] = row.get_text
            return row

        return None

    def _drives_expander(self, opt: opts.Option) -> Adw.ExpanderRow:
        expander = Adw.ExpanderRow(
            title=opt.label,
            subtitle=_("A Linux directory appears as a drive in Windows"),
        )
        rows: list[Adw.ExpanderRow] = []

        def add_drive(name: str = "share", path: str = "") -> None:
            drive = self._drive_row(name, path, on_remove=None)
            rows.append(drive)
            expander.add_row(drive)

        def remove_drive(drive: Adw.ExpanderRow) -> None:
            rows.remove(drive)
            expander.remove(drive)

        for name, path in self._profile.values.get(opt.key, ()) or ():
            drive = self._drive_row(name, path, on_remove=remove_drive)
            rows.append(drive)
            expander.add_row(drive)

        add_row = Adw.ButtonRow(title=_("Add a drive"))
        add_row.connect("activated", lambda *_: add_drive())
        expander.add_row(add_row)

        self._getters[opt.key] = lambda: tuple(
            (r._drive_name.get_text().strip() or "share", r._drive_path.get_text().strip())
            for r in rows
            if r._drive_path.get_text().strip()
        )
        return expander

    def _drive_row(
        self,
        name: str,
        path: str,
        on_remove: Callable[[Adw.ExpanderRow], None] | None,
    ) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow(title=name or "share", subtitle=path or _("no folder selected"))
        row._drive_name = Adw.EntryRow(title=_("Drive name in Windows"))
        row._drive_name.set_text(name)
        row._drive_path = Adw.EntryRow(title=_("Folder on this machine"))
        row._drive_path.set_text(path)

        def refresh(*_args: Any) -> None:
            row.set_title(row._drive_name.get_text().strip() or "share")
            row.set_subtitle(row._drive_path.get_text().strip() or _("no folder selected"))

        row._drive_name.connect("changed", refresh)
        row._drive_path.connect("changed", refresh)
        row.add_row(row._drive_name)
        row.add_row(row._drive_path)

        choose = Adw.ButtonRow(title=_("Choose a folder…"))
        choose.connect("activated", lambda *_: self._choose_folder(row._drive_path))
        row.add_row(choose)

        if on_remove is not None:
            remove = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            remove.add_css_class("flat")
            remove.set_tooltip_text(_("Remove the drive"))
            remove.connect("clicked", lambda *_: on_remove(row))
            row.add_suffix(remove)
        return row

    def _choose_folder(self, target: Adw.EntryRow) -> None:
        dialog = Gtk.FileDialog(title=_("Choose a folder"))

        def done(source: Gtk.FileDialog, result: Any) -> None:
            try:
                folder = source.select_folder_finish(result)
            except Exception:
                return
            if folder is not None:
                target.set_text(folder.get_path() or "")

        dialog.select_folder(parent=self, callback=done)

    # ---------------------------------------------------------------- сохранить
    def _save(self, *_args: Any) -> None:
        profile = self._profile
        profile.name = self._name.get_text().strip() or _("Connection")
        profile.host = self._host.get_text().strip()
        profile.port = int(self._port.get_value())
        profile.username = self._username.get_text().strip()
        profile.domain = self._domain.get_text().strip()
        for key, getter in self._getters.items():
            profile.values[key] = getter()
        profile.values = opts.normalize(profile.values)

        typed = self._password.get_text()
        remember = self._remember.get_active()
        self._on_save(profile, typed if typed else None, remember)
        self.close()
