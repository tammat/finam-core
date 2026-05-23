#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_session_classifier.py \
  src/scripts/build_futures_session_analytics.py

python - <<'PY'
from datetime import datetime, timezone
from finam_core.research.futures_session_classifier import classify_futures_session

assert classify_futures_session(datetime(2026, 5, 22, 6, 30, tzinfo=timezone.utc)) == "MOEX_MORNING"
assert classify_futures_session(datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc)) == "MOEX_DAY"

# Русский комментарий: летом NY 09:30 = 13:30 UTC = 16:30 MSK.
assert classify_futures_session(datetime(2026, 5, 22, 13, 30, tzinfo=timezone.utc)) == "US_OPEN_WINDOW"

# Русский комментарий: зимой NY 09:30 = 14:30 UTC = 17:30 MSK.
assert classify_futures_session(datetime(2026, 1, 22, 14, 30, tzinfo=timezone.utc)) == "US_OPEN_WINDOW"

assert classify_futures_session(datetime(2026, 5, 22, 18, 0, tzinfo=timezone.utc)) == "MOEX_EVENING"

print("TEST_FUTURES_SESSION_ANALYTICS_OK")
PY
