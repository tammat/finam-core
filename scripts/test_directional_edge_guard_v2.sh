#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/directional_edge_guard.py \
  src/scripts/check_directional_edge_guard.py

python - <<'PY'
from finam_core.analytics.directional_edge_guard import DirectionalEdgeGuard

guard = DirectionalEdgeGuard()

sell_ok = guard.decide(
    symbol="BRN6@RTSX",
    continuous_symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    side="SELL",
    regime_direction="trend_down",
    guard_status="favorable",
)
assert sell_ok.status == "confirmed"
assert sell_ok.reason == "EDGE_DIRECTION_CONFIRMED"

buy_bad = guard.decide(
    symbol="BRN6@RTSX",
    continuous_symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    side="BUY",
    regime_direction="trend_up",
    guard_status="unfavorable",
)
assert buy_bad.status == "mismatch"
assert buy_bad.reason == "EDGE_DIRECTION_MISMATCH"

unknown = guard.decide(
    symbol="BRN6@RTSX",
    continuous_symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    side="BUY",
    regime_direction="unknown",
    guard_status=None,
)
assert unknown.status == "unknown"

print("DIRECTIONAL_EDGE_GUARD_V2_UNIT_OK")
PY

python src/scripts/check_directional_edge_guard.py --help | grep -q -- "--regime-direction"

echo "DIRECTIONAL_EDGE_GUARD_V2_COMPILE_OK"
