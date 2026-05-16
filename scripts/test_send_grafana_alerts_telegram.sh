#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_telegram_alert_delivery.sql >/dev/null

python -m py_compile src/scripts/send_grafana_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/send_grafana_alerts_telegram.py").read_text(encoding="utf-8")

checks = [
    "v_grafana_alerts_ru",
    "telegram_alert_delivery",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "Finam Core Alert",
    "on conflict",
]

for c in checks:
    assert c in text, c

print("OK: Telegram Grafana alert bridge static check")
PY

PYTHONPATH=src python src/scripts/send_grafana_alerts_telegram.py
