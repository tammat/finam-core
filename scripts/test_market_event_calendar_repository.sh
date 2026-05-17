#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_market_event_calendar.sql >/dev/null

python -m py_compile \
  src/finam_core/risk/market_event_calendar_repository.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/risk/market_event_calendar_repository.py").read_text(encoding="utf-8")

checks = [
    "MarketEventCalendarRepository",
    "MarketEventContext",
    "CBR_RATE_DECISION",
    "EIA_INVENTORY",
    "minutes_to_event",
    "market_event_calendar",
]

for c in checks:
    assert c in text, c

print("OK: MarketEventCalendarRepository static check")
PY
