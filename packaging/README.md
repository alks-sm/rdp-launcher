# Упаковка

## RPM (Fedora / COPR)

Спецификация: [`rdp-launcher.spec`](rdp-launcher.spec). Пакет собирается как `noarch`:
приложение чисто на Python, а клиент `sdl-freerdp` подключается как зависимость.

Раскладка пакета намеренно самодостаточна:

```
/usr/bin/rdp-launcher                 обёртка: PYTHONPATH=/usr/share/rdp-launcher python3 -m rdp_launcher
/usr/share/rdp-launcher/rdp_launcher/ код
/usr/share/rdp-launcher/locale/       переводы (i18n.py ищет их рядом с пакетом)
/usr/share/applications/…desktop
/usr/share/icons/hicolor/scalable/apps/…svg
/usr/share/metainfo/…metainfo.xml
/usr/share/mime/packages/x-rdp.xml
```

### Локальная сборка

```bash
sudo dnf install rpm-build gettext desktop-file-utils tar gzip
VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
mkdir -p ~/rpmbuild/{SOURCES,SRPMS,RPMS,BUILD,BUILDROOT}
tar --transform "s,^\.,rdp-launcher-$VERSION," --exclude=.git --exclude=__pycache__ \
    -czf ~/rpmbuild/SOURCES/rdp-launcher-$VERSION.tar.gz .
rpmbuild -ba packaging/rdp-launcher.spec

sudo dnf install ~/rpmbuild/RPMS/noarch/rdp-launcher-$VERSION-1*.noarch.rpm
```

Этот же путь прогоняется в CI (задача `rpm` в `.github/workflows/ci.yml`),
поэтому спецификация проверяется на каждой сборке, а не «на глаз».

### Публикация в COPR

Нужен аккаунт [copr.fedorainfracloud.org](https://copr.fedorainfracloud.org/).

```bash
sudo dnf install copr-cli
# токен: https://copr.fedorainfracloud.org/api/
cat > ~/.config/copr <<'EOF'
[copr-cli]
username = <ваш логин>
login = <ваш логин>
token = <API-токен>
copr_url = https://copr.fedorainfracloud.org
EOF

copr-cli create rdp-launcher \
  --chroot fedora-44-x86_64 --chroot fedora-44-aarch64 \
  --description "Minimal GTK4 front-end for the official FreeRDP client" \
  --enable-net on

# сборка прямо из git: .copr/Makefile соберёт tarball из рабочего дерева
copr-cli buildscm rdp-launcher \
  --clone-url https://github.com/alks-sm/rdp-launcher \
  --commit main --method make_srpm
```

Через веб-интерфейс: *New Project* → тип сборки **SCM** → указать git-ссылку,
ветку `main` и способ создания SRPM **make_srpm** (используется `.copr/Makefile`).

## Что стоит учесть

* Пакет `noarch`, но зависит от `freerdp` — конкретную версию клиента выбирает дистрибутив.
  Приложение работает с любой версией: оно не линкуется с `libfreerdp`, а только запускает
  бинарник, поэтому пересборка при обновлении FreeRDP не требуется.
* Флаги клиента проверяются тестом на реальном `sdl-freerdp` (`tests/test_core.py`).
  В сборочном окружении `freerdp` нет в `BuildRequires`, поэтому этот тест там
  пропускается — сознательно: иначе обновление FreeRDP в апстриме ломало бы сборку пакета.
* Flatpak сознательно не рассматривается: приложение по своей сути запускает клиент
  с хоста, а внутри песочницы это требует `--talk-name=org.freedesktop.Flatpak`
  и отдельной проработки.
