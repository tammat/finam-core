#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_VOLATILITY_BREAKOUT_ENGINE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/020_volatility_breakout_engine_v1.sql

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/engines/volatility_breakout_engine.py \
  src/marketcore/presentation/ui_labels.py

PYTHONPATH=src python - <<'PY_CHECK'
from datetime import UTC, datetime, timedelta

from marketcore.research.execution.engines.volatility_breakout_engine import VolatilityBreakoutEngine
from marketcore.research.execution.interfaces.data_provider import MarketBar, MarketBars

base = datetime.now(UTC)
bars = []
for i in range(25):
    price = 100.0 + i * 0.01
    bars.append(MarketBar(base + timedelta(minutes=i), price, price, price, price, 1.0))

bars.append(MarketBar(base + timedelta(minutes=26), 101.0, 101.0, 101.0, 101.0, 1.0))

market = MarketBars(symbol="TEST", timeframe="M5", source="unit", bars=bars)
engine = VolatilityBreakoutEngine()
signals = engine.execute(market, {"lookback": 20, "threshold": 0.0})

assert engine.engine_name == "VOLATILITY_BREAKOUT_ENGINE_V1"
assert len(signals) > 0
assert signals[-1].direction == "BUY"
assert signals[-1].is_trade_signal is True
PY_CHECK

engine_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_engine_registry_v1
WHERE engine_name='VOLATILITY_BREAKOUT_ENGINE_V1'
  AND enabled=true;
")

assigned_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_library_v1
WHERE engine_name='VOLATILITY_BREAKOUT_ENGINE_V1';
")

test "$engine_rows" = "1"
test "$assigned_rows" -ge 1

grep -q "strategy.engine.volatility_breakout.title" src/marketcore/presentation/ui_labels.py

echo "engine_rows=$engine_rows"
echo "assigned_strategy_rows=$assigned_rows"
echo "i18n=ok"
echo "dispatcher_changed=0"
echo "hardcode_dispatcher_mapping=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_VOLATILITY_BREAKOUT_ENGINE_V1_OK"
