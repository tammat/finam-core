#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/market_event_risk.py \
  src/scripts/build_strategy_event_risk_context.py

python - <<'PY'
from datetime import datetime, timezone, timedelta
from finam_core.research.market_event_risk import decide_market_event_risk

d = decide_market_event_risk(
    now=datetime.now(timezone.utc),
    nearest_event_ts=datetime.now(timezone.utc) + timedelta(minutes=10),
    impact="HIGH",
)
assert d.status == "EVENT_ACTIVE"
assert d.allow_runtime is False
print("TEST_STRATEGY_EVENT_RISK_CONTEXT_OK")
PY
