#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python -m py_compile \
  src/finam_core/ai/telegram_bot_news_ingest.py

python - <<'PY'
from finam_core.ai.telegram_bot_news_ingest import TelegramBotNewsIngest

print("OK: telegram_bot_news_ingest import successful")
print("Class:", TelegramBotNewsIngest)
PY

echo "OK: telegram_bot_news_ingest compile test passed"
