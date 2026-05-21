#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.notifications.telegram_signal_router import route_telegram_signal

paper_bad = route_telegram_signal(channel_type="PAPER", confidence=0.65)
assert paper_bad.should_send is False
assert paper_bad.target_env == "TELEGRAM_PAPER_LAB_CHAT_ID"

paper_good = route_telegram_signal(channel_type="PAPER", confidence=0.75)
assert paper_good.should_send is True

radar_good = route_telegram_signal(channel_type="RADAR", confidence=0.61)
assert radar_good.should_send is True
assert radar_good.target_env == "TELEGRAM_MARKET_RADAR_CHAT_ID"

risk = route_telegram_signal(channel_type="RISK", confidence=0.0)
assert risk.should_send is True
assert risk.target_env == "TELEGRAM_REAL_DESK_CHAT_ID"

print("TEST_TELEGRAM_SIGNAL_ROUTER_OK")
PY

python -m py_compile \
  src/finam_core/notifications/telegram_signal_taxonomy.py \
  src/finam_core/notifications/telegram_signal_router.py
