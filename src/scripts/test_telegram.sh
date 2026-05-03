#!/bin/bash
set -e

# Жёстко задаём путь проекта (исправляет проблемы запуска из любой директории)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# Подключаем PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src"

# Загружаем .env (ключевой фикс)

if [ -f "$PROJECT_ROOT/.env" ]; then
  # корректная загрузка .env (игнор комментариев и пустых строк)
  # безопасная загрузка .env (ТОЛЬКО KEY=VALUE)
  while IFS= read -r line; do
    if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      export "$line"
    fi
  done < "$PROJECT_ROOT/.env"
fi

# === ENV VALIDATION ===
if [ -z "$TG_TOKEN" ] || [ -z "$TG_CHAT_ID" ]; then
  echo "ENV ERROR: TG_TOKEN or TG_CHAT_ID missing"
  exit 1
fi

# алиас для кода
export TG_BOT_TOKEN="$TG_TOKEN"
export ENABLE_TELEGRAM_NOTIFIER=1

echo "=== TELEGRAM ENV CHECK ==="
echo "TOKEN=${TG_BOT_TOKEN:0:6}***"
echo "CHAT=$TG_CHAT_ID"
echo "ENABLED=$ENABLE_TELEGRAM_NOTIFIER"

# проверка python
which python3 || { echo "python3 not found"; exit 1; }

python3 - <<EOF
from finam_core.notifications.telegram_notifier import TelegramNotifier
TelegramNotifier().send("🚀 FINAM CORE PROD TELEGRAM OK")
EOF

if [ $? -eq 0 ]; then
  echo "TEST PASSED"
  exit 0
else
  echo "TEST FAILED"
  exit 1
fi