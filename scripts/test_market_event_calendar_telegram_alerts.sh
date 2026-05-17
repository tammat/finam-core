#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_market_event_calendar_alerts_view.sql >/dev/null

python -m py_compile src/scripts/send_market_event_calendar_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/send_market_event_calendar_alerts_telegram.py").read_text(encoding="utf-8")

checks = [
    "v_market_event_calendar_alerts_ru",
    "Календарное событие рынка",
    "Режим исполнения",
    "TG_ALERT_BOT_TOKEN",
    "telegram_alert_delivery",
    "market_event|",
]

for c in checks:
    assert c in text, c

print("OK: market event calendar Telegram alerts static check")
PY

psql "$DATABASE_URL" -P pager=off -c "
select *
from v_market_event_calendar_alerts_ru
limit 20;
"

echo "OK: market event calendar Telegram alerts"
