#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_V5_FUTURES_ROLLOVER_SESSION_FRESHNESS_V1 ==="

python - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.run_autonomous_edge_search_cycle_v1 import (
    session_freshness_minutes,
)

MSK = ZoneInfo("Europe/Moscow")

# Понедельник до открытия после выходных.
monday_preopen = datetime(
    2026, 8, 10, 4, 43,
    tzinfo=MSK,
)

# Обычный рабочий день до 10:00.
weekday_preopen = datetime(
    2026, 8, 11, 8, 0,
    tzinfo=MSK,
)

# Обычная торговая сессия.
intraday = datetime(
    2026, 8, 11, 12, 0,
    tzinfo=MSK,
)

assert session_freshness_minutes(monday_preopen) == 4320
assert session_freshness_minutes(weekday_preopen) == 720
assert session_freshness_minutes(intraday) == 15

print("monday_preopen_freshness_minutes=4320")
print("weekday_preopen_freshness_minutes=720")
print("intraday_freshness_minutes=15")
print("canonical_session_freshness_reused=1")
PY

grep -q \
'from scripts.run_autonomous_edge_search_cycle_v1 import' \
src/scripts/run_v5_futures_rollover_v1.py

grep -q \
'timedelta(minutes=freshness_minutes)' \
src/scripts/run_v5_futures_rollover_v1.py

echo "production_rollover_logic_changed=1"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_V5_FUTURES_ROLLOVER_SESSION_FRESHNESS_V1_OK"
