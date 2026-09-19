#!/usr/bin/env bash
# Сборка каталогов переводов.
#
#   ./tools/build-locales.sh                 # обновить шаблон и скомпилировать все po/*.po
#   ./tools/build-locales.sh --update        # ещё и подтянуть новые строки в переводы
#   ./tools/build-locales.sh --compile-only  # только скомпилировать (шаблон не трогать)
#
# Исходный язык строк в коде — английский. Переводы лежат в po/<lang>.po,
# результат компиляции — locale/<lang>/LC_MESSAGES/rdp-launcher.mo.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

DOMAIN="rdp-launcher"
MODE="${1:-}"

for tool in xgettext msgfmt; do
  command -v "$tool" >/dev/null || { echo "нужен пакет gettext (нет $tool)"; exit 1; }
done

VERSION="$(python3 -c 'import re,pathlib; m=re.search(r"^version = \"([^\"]+)\"", pathlib.Path("pyproject.toml").read_text(encoding="utf-8"), re.M); print(m.group(1) if m else "0.0.0")')"

mkdir -p po locale

if [ "$MODE" != "--compile-only" ]; then
  # 1. Шаблон со всеми строками, помеченными _()
  # Порядок файлов сортируем: xgettext сохраняет порядок входа, а find его не гарантирует —
  # без сортировки шаблон отличается от машины к машине.
  mapfile -t sources < <(find rdp_launcher -name '*.py' ! -name 'i18n.py' | LC_ALL=C sort)
  xgettext \
    --language=Python \
    --keyword=_ \
    --from-code=UTF-8 \
    --package-name="$DOMAIN" \
    --package-version="$VERSION" \
    --output="po/$DOMAIN.pot" \
    "${sources[@]}"
  echo "шаблон обновлён: po/$DOMAIN.pot ($(grep -c '^msgid "' "po/$DOMAIN.pot") строк)"

  # 2. При --update подтянуть новые строки в переводы (старые сохраняются)
  if [ "$MODE" = "--update" ]; then
    shopt -s nullglob
    for po in po/*.po; do
      msgmerge --update --backup=none "$po" "po/$DOMAIN.pot"
      echo "обновлён: $po"
    done
    shopt -u nullglob
  fi
fi

# 3. Компиляция
shopt -s nullglob
found=0
for po in po/*.po; do
  lang="$(basename "$po" .po)"
  mkdir -p "locale/$lang/LC_MESSAGES"
  msgfmt --check -o "locale/$lang/LC_MESSAGES/$DOMAIN.mo" "$po"
  printf '  %-6s %s\n' "$lang" "locale/$lang/LC_MESSAGES/$DOMAIN.mo"
  found=$((found + 1))
done
shopt -u nullglob
echo "скомпилировано переводов: $found"
