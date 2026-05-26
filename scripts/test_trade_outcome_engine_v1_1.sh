#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/trade_outcome_engine.py \
  src/scripts/build_trade_outcomes.py

python - <<'PY'
from datetime import datetime, timezone
from finam_core.analytics.trade_outcome_engine import TradeFill, TradeOutcomeEngine

ts = datetime.now(timezone.utc)

fills = [
    TradeFill(1, "BRN6@RTSX", "BUY", 1.0, 100.0, 0.0, ts, "e1", "paper", "BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT", {"run_id": "A"}),
    TradeFill(2, "BRN6@RTSX", "SELL", 1.0, 101.0, 0.0, ts, "x1", "paper", "BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT", {"run_id": "B"}),
]

outcomes = TradeOutcomeEngine().build(fills)
assert len(outcomes) == 0, "cross-run fills must not be matched"

fills2 = [
    TradeFill(3, "BRN6@RTSX", "BUY", 1.0, 100.0, 0.0, ts, "e2", "paper", "BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT", {"run_id": "C"}),
    TradeFill(4, "BRN6@RTSX", "SELL", 1.0, 101.5, 0.0, ts, "x2", "paper", "BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT", {"run_id": "C"}),
]

outcomes2 = TradeOutcomeEngine().build(fills2)
assert len(outcomes2) == 1
assert round(outcomes2[0].net_pnl, 4) == 1.5
assert outcomes2[0].raw_json["outcome_engine_version"] == "trade_outcome_engine_v1_1"

print("TRADE_OUTCOME_ENGINE_V1_1_UNIT_OK")
PY

python src/scripts/build_trade_outcomes.py --help | grep -q -- "--max-holding-minutes"

echo "TRADE_OUTCOME_ENGINE_V1_1_COMPILE_OK"
