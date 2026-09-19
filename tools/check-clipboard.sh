#!/usr/bin/env bash
# Диагностика буфера обмена для RDP.
#
# Отвечает на вопрос: текст испортил FreeRDP или он уже лежал в буфере обмена
# в испорченном виде (например, приложение-источник записало его с экранированием
# вида \u0427\u0442\u043e).
#
#   ./check-clipboard.sh            # посмотреть, что сейчас в буфере
#   ./check-clipboard.sh --selftest # положить контрольную строку и проверить её же
set -euo pipefail

have() { command -v "$1" >/dev/null 2>&1; }

if ! have wl-paste; then
  echo "Нужен пакет wl-clipboard:  sudo dnf install wl-clipboard"
  exit 1
fi

read_clipboard() {
  # -n — без завершающего перевода строки; игнорируем пустой/недоступный буфер
  timeout 3 wl-paste -n 2>/dev/null || true
}

show() {
  local text="$1"
  echo "--- что лежит в буфере обмена ---"
  printf '%s\n' "$text"
  echo "--- анализ ---"
  echo "длина: ${#text} символов"
  if printf '%s' "$text" | grep -qE '\\u[0-9a-fA-F]{4}'; then
    echo "НАЙДЕНО экранирование \\uXXXX — текст уже испорчен ДО RDP."
    echo "Значит виновато приложение-источник, а не клиент. Проверьте, откуда копируете:"
    echo "  * веб-интерфейсы и Electron-приложения иногда кладут в буфер JSON-строку;"
    echo "  * терминал может скопировать то, что показывает, включая escape-последовательности."
    python3 - "$text" <<'PY' 2>/dev/null || true
import re, sys
text = sys.argv[1]
def decode(match: "re.Match[str]") -> str:
    return chr(int(match.group(1), 16))
print("если раскодировать, получится:", re.sub(r"\\u([0-9a-fA-F]{4})", decode, text))
PY
  elif printf '%s' "$text" | LC_ALL=C grep -qP '[\x80-\xFF]'; then
    echo "В буфере настоящий UTF-8 (многобайтовые символы). Источник чист."
    echo "Если в Windows всё равно приходит мусор — проблема на стороне клиента или сервера."
  else
    echo "Только ASCII — кириллицы в буфере нет."
  fi
}

if [ "${1:-}" = "--selftest" ]; then
  if ! have wl-copy; then
    echo "Нужен wl-copy (пакет wl-clipboard)"; exit 1
  fi
  sample='Проверка буфера: что дал главный принцип — 42.'
  printf '%s' "$sample" | wl-copy
  sleep 1
  echo "=== 1. Кладём контрольную строку в буфер ==="
  echo "$sample"
  echo
  echo "=== 2. Читаем обратно ==="
  roundtrip=$(read_clipboard)
  if [ "$roundtrip" = "$sample" ]; then
    echo "буфер отдаёт ровно то, что положили — клипборд в порядке."
  else
    echo "НЕ СОВПАДАЕТ:"
    printf '  положили: %s\n  получили: %s\n' "$sample" "$roundtrip"
  fi
  echo
  echo "=== 3. Теперь вставьте это в Windows (Ctrl+V) ==="
  echo "Буфер проверен как чистый, поэтому:"
  echo "  пришло 'Проверка буфера: что дал главный принцип — 42.'  -> всё в порядке;"
  echo "  пришло с \\uXXXX                                        -> экранирует уже RDP-стек"
  echo "                                                            (клиент или сервер), это баг."
  exit 0
fi

show "$(read_clipboard)"
