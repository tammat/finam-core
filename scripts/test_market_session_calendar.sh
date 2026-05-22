#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/session/market_session_calendar.py

python - <<'PY'
from datetime import datetime, timezone
from finam_core.session.market_session_calendar import MarketSessionCalendar

c = MarketSessionCalendar()

assert c.is_open(symbol="BRM6@RTSX", ts=datetime(2026, 5, 4, 7, 0, tzinfo=timezone.utc)) is True
assert c.is_open(symbol="BRM6@RTSX", ts=datetime(2026, 5, 4, 2, 0, tzinfo=timezone.utc)) is False
assert c.is_open(symbol="BRM6@RTSX", ts=datetime(2026, 5, 9, 10, 0, tzinfo=timezone.utc)) is False

assert c.has_open_time_between(
    symbol="BRM6@RTSX",
    start_ts=datetime(2026, 5, 4, 20, 45, tzinfo=timezone.utc),
    end_ts=datetime(2026, 5, 5, 5, 55, tzinfo=timezone.utc),
    step_minutes=5,
) is False

assert c.has_open_time_between(
    symbol="BRM6@RTSX",
    start_ts=datetime(2026, 5, 4, 6, 0, tzinfo=timezone.utc),
    end_ts=datetime(2026, 5, 4, 7, 0, tzinfo=timezone.utc),
    step_minutes=5,
) is True

print("TEST_MARKET_SESSION_CALENDAR_OK")
PY
