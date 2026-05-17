#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_market_event_calendar.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_event_calendar.py").read_text(encoding="utf-8")

checks = [
    "market_event_calendar",
    "MARKET_EVENT_CALENDAR_TSV",
    "pre_event_block_min",
    "pre_event_reduce_min",
    "instrument_group",
    "event_type",
]

for c in checks:
    assert c in text, c

print("OK: market event calendar updater static check")
PY

PYTHONPATH=src python src/scripts/update_market_event_calendar.py

psql "$DATABASE_URL" -P pager=off -c "
select event_time, event_type, instrument_group, event_name, severity, source
from market_event_calendar
order by event_time
limit 20;
"

echo "OK: market event calendar updater"
