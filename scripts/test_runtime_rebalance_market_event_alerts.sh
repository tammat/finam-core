#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_rebalance_loop.py \
  src/scripts/send_market_event_calendar_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/runtime_rebalance_loop.py").read_text(encoding="utf-8")

assert "update_market_event_calendar.py" in text
assert "send_market_event_calendar_alerts_telegram.py" in text

update_pos = text.find("update_market_event_calendar.py")
alert_pos = text.find("send_market_event_calendar_alerts_telegram.py")

assert update_pos < alert_pos

print("OK: runtime rebalance sends market event calendar alerts after update")
PY
