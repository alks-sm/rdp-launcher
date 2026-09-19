%global app_id io.github.rdplauncher.RdpLauncher

Name:           rdp-launcher
Version:        0.1.0
Release:        1%{?dist}
Summary:        Minimal GTK4 front-end for the official FreeRDP client

License:        MIT
URL:            https://github.com/alks-sm/rdp-launcher
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  gettext
BuildRequires:  desktop-file-utils

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       libsecret
Requires:       freerdp

%description
A minimal GTK4/libadwaita front-end for the official FreeRDP client.

Instead of embedding libfreerdp — the approach taken by Remmina, KRDC and
GNOME Connections — it builds a command line and launches sdl-freerdp, the
current SDL3 client that runs natively on Wayland, as a separate process.
That avoids XWayland blur, isolates crashes, removes any ABI coupling to
FreeRDP, and allows several sessions at once.

Features: connection profiles, display/audio/drive settings, passwords in the
GNOME keyring (libsecret), .rdp import and export.

%prep
%autosetup -n %{name}-%{version}

%build
# Переводы компилируются из po/, чтобы пакет не зависел от того,
# закоммичены ли собранные .mo-файлы.
./tools/build-locales.sh --compile-only

%install
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -r rdp_launcher %{buildroot}%{_datadir}/%{name}/
find %{buildroot}%{_datadir}/%{name} -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
cp -r locale %{buildroot}%{_datadir}/%{name}/

install -dpm 0755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/%{name} <<'EOF'
#!/bin/sh
# i18n.py ищет каталог переводов рядом с пакетом: %{_datadir}/rdp-launcher/locale
exec env PYTHONPATH=%{_datadir}/%{name} python3 -m rdp_launcher "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/%{name}

install -Dpm 0644 data/%{app_id}.svg \
  %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{app_id}.svg
install -Dpm 0644 data/%{app_id}.metainfo.xml \
  %{buildroot}%{_datadir}/metainfo/%{app_id}.metainfo.xml
install -Dpm 0644 data/application-x-rdp.xml \
  %{buildroot}%{_datadir}/mime/packages/x-rdp.xml

sed -e 's|@EXEC@|%{name} %F|' -e 's|@ICON@|%{app_id}|' \
  data/%{app_id}.desktop.in > %{app_id}.desktop
install -Dpm 0644 %{app_id}.desktop \
  %{buildroot}%{_datadir}/applications/%{app_id}.desktop

desktop-file-validate %{buildroot}%{_datadir}/applications/%{app_id}.desktop

%check
# Тесты логики. Проверка флагов на реальном клиенте здесь пропускается:
# freerdp нет в BuildRequires, чтобы обновление апстрима не ломало сборку пакета.
# GUI-тест требует дисплея и в сборочном окружении не запускается.
python3 -m compileall -q %{buildroot}%{_datadir}/%{name}/rdp_launcher
PYTHONPATH=%{_builddir}/%{name}-%{version} python3 tests/test_core.py

%files
%license LICENSE
%doc README.md docs
%{_bindir}/%{name}
%{_datadir}/%{name}
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{app_id}.svg
%{_datadir}/metainfo/%{app_id}.metainfo.xml
%{_datadir}/mime/packages/x-rdp.xml

%changelog
* Sat Sep 19 2026 alks-sm <222426423+alks-sm@users.noreply.github.com> - 0.1.0-1
- Initial package
