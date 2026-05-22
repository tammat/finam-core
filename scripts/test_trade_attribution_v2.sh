#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.trade_attribution_v2 import classify_trade_attribution_quality

q, reason = classify_trade_attribution_quality(
    strategy="br_conservative_breakout",
    timeframe="M5",
    heat_status="HIGH",
    lifecycle_action="NO_ACTION",
    exit_policy="take50_stop50",
)
assert q == "FULL"

q2, reason2 = classify_trade_attribution_quality(
    strategy="",
    timeframe="M5",
    heat_status="unknown",
    lifecycle_action="NO_ACTION",
    exit_policy="",
)
assert q2 == "PARTIAL"

q3, reason3 = classify_trade_attribution_quality(
    strategy="x",
    timeframe="M5",
    heat_status="HIGH",
    lifecycle_action="SYNC_LIFECYCLE_QTY",
    exit_policy="p",
)
assert q3 == "RISK_CONTEXT_WEAK"

print("TEST_TRADE_ATTRIBUTION_V2_OK")
PY

python -m py_compile \
  src/finam_core/analytics/trade_attribution_v2.py \
  src/finam_core/analytics/trade_attribution_v2_repository.py \
  src/scripts/build_trade_attribution_v2.py
