#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/trade_outcome_engine.py \
  src/scripts/build_trade_outcomes.py

python - <<'PY'
from datetime import datetime, timezone
from finam_core.analytics.trade_outcome_engine import TradeFill, TradeOutcomeEngine

fills = [
    TradeFill(1, "BRN6@RTSX", "BUY", 1.0, 100.0, 0.0, datetime.now(timezone.utc), "e1", "paper", "BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT", {}),
    TradeFill(2, "BRN6@RTSX", "SELL", 1.0, 101.5, 0.0, datetime.now(timezone.utc), "x1", "paper", "BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT", {}),
]

outcomes = TradeOutcomeEngine().build(fills)
assert len(outcomes) == 1
assert round(outcomes[0].net_pnl, 4) == 1.5
assert outcomes[0].continuous_symbol == "BR_CONT"

print("TRADE_OUTCOME_ENGINE_UNIT_OK")
PY

echo "TRADE_OUTCOME_ENGINE_COMPILE_OK"
