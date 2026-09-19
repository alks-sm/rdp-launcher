#!/usr/bin/env bash
# Установка RDP Launcher для текущего пользователя (без root).
#
#   ./install.sh            # установить ярлык, иконку, MIME-тип .rdp
#   ./install.sh --uninstall
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ID="io.github.rdplauncher.RdpLauncher"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
MIME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/mime/packages"
METAINFO_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/metainfo"

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$DESKTOP_DIR/$APP_ID.desktop" "$ICON_DIR/$APP_ID.svg" "$MIME_DIR/x-rdp.xml"
  rm -f "$METAINFO_DIR/$APP_ID.metainfo.xml"
  command -v update-desktop-database >/dev/null && update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
  command -v update-mime-database >/dev/null && update-mime-database "${XDG_DATA_HOME:-$HOME/.local/share}/mime" 2>/dev/null || true
  echo "Удалено."
  exit 0
fi

# Проверка зависимостей
missing=()
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null \
  || missing+=("python3-gobject gtk4 libadwaita")
python3 -c "import gi; gi.require_version('Secret','1'); from gi.repository import Secret" 2>/dev/null \
  || missing+=("libsecret (python3-gobject-base)")
command -v sdl-freerdp >/dev/null || command -v xfreerdp >/dev/null \
  || missing+=("freerdp")
if [ ${#missing[@]} -gt 0 ]; then
  echo "Не хватает: ${missing[*]}"
  echo "Установите:  sudo dnf install freerdp python3-gobject gtk4 libadwaita libsecret"
  exit 1
fi

mkdir -p "$DESKTOP_DIR" "$ICON_DIR" "$MIME_DIR" "$METAINFO_DIR"

EXEC="env PYTHONPATH=$HERE python3 -m rdp_launcher %F"
sed -e "s|@EXEC@|$EXEC|" -e "s|@ICON@|$APP_ID|" \
  "$HERE/data/$APP_ID.desktop.in" > "$DESKTOP_DIR/$APP_ID.desktop"

cp "$HERE/data/$APP_ID.svg" "$ICON_DIR/$APP_ID.svg"
cp "$HERE/data/application-x-rdp.xml" "$MIME_DIR/x-rdp.xml"
cp "$HERE/data/$APP_ID.metainfo.xml" "$METAINFO_DIR/$APP_ID.metainfo.xml"

command -v xdg-mime >/dev/null && xdg-mime install "$HERE/data/application-x-rdp.xml" 2>/dev/null || true
command -v xdg-mime >/dev/null && xdg-mime default "$APP_ID.desktop" application/x-rdp 2>/dev/null || true
command -v update-desktop-database >/dev/null && update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
command -v update-mime-database >/dev/null && update-mime-database "${XDG_DATA_HOME:-$HOME/.local/share}/mime" 2>/dev/null || true
command -v gtk4-update-icon-cache >/dev/null && gtk4-update-icon-cache -f -t "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" 2>/dev/null || true

echo "Установлено:"
echo "  ярлык:  $DESKTOP_DIR/$APP_ID.desktop"
echo "  иконка: $ICON_DIR/$APP_ID.svg"
echo "  .rdp:   связан с приложением (application/x-rdp)"
echo
echo "Запуск: ищите «RDP Launcher» в меню приложений или:"
echo "  PYTHONPATH=$HERE python3 -m rdp_launcher"
