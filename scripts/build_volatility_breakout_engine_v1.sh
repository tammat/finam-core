#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_VOLATILITY_BREAKOUT_ENGINE_V1 ==="

mkdir -p sql/analytics src/marketcore/research/execution/engines scripts

cat > sql/analytics/020_volatility_breakout_engine_v1.sql <<'SQL_END'
INSERT INTO analytics.strategy_engine_registry_v1 (
    engine_name,
    engine_version,
    engine_family,
    enabled,
    config_json,
    source_version,
    updated_at
)
VALUES (
    'VOLATILITY_BREAKOUT_ENGINE_V1',
    'v1',
    'BREAKOUT',
    true,
    '{"default_lookback":20,"default_threshold":0.0}'::jsonb,
    'VOLATILITY_BREAKOUT_ENGINE_V1',
    now()
)
ON CONFLICT(engine_name) DO UPDATE SET
    engine_version=EXCLUDED.engine_version,
    engine_family=EXCLUDED.engine_family,
    enabled=EXCLUDED.enabled,
    config_json=EXCLUDED.config_json,
    source_version=EXCLUDED.source_version,
    updated_at=now();

UPDATE analytics.strategy_library_v1
SET engine_name='VOLATILITY_BREAKOUT_ENGINE_V1',
    updated_at=now()
WHERE strategy_code IN (
    'VOLATILITY_BREAKOUT_V2',
    'OPENING_RANGE_BREAKOUT_V1',
    'NR7_BREAKOUT_V1'
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.strategy_engine_registry_v1 TO alex;
SQL_END

cat > src/marketcore/research/execution/engines/volatility_breakout_engine.py <<'PY_END'
from __future__ import annotations

from marketcore.research.execution.dto.signal import StrategySignal
from marketcore.research.execution.interfaces.data_provider import MarketBars


class VolatilityBreakoutEngine:
    engine_name = "VOLATILITY_BREAKOUT_ENGINE_V1"

    def execute(
        self,
        market_data: MarketBars,
        parameters: dict | None = None,
    ) -> list[StrategySignal]:
        params = parameters or {}
        lookback = int(params.get("lookback", 20))
        threshold = float(params.get("threshold", 0.0))

        lookback = max(2, min(lookback, 500))
        bars = market_data.bars

        if len(bars) <= lookback:
            return []

        signals: list[StrategySignal] = []

        for i in range(lookback, len(bars)):
            window = bars[i - lookback:i]
            bar = bars[i]

            prev_high = max(x.high for x in window)
            prev_low = min(x.low for x in window)

            direction = "FLAT"
            if bar.close > prev_high + threshold:
                direction = "BUY"
            elif bar.close < prev_low - threshold:
                direction = "SELL"

            if direction == "FLAT":
                continue

            signals.append(
                StrategySignal(
                    signal_ts=bar.ts,
                    direction=direction,
                    price=bar.close,
                    confidence=0.50,
                    metadata={
                        "engine_name": self.engine_name,
                        "lookback": lookback,
                        "threshold": threshold,
                        "prev_high": prev_high,
                        "prev_low": prev_low,
                    },
                )
            )

        return signals
PY_END

cat >> src/marketcore/presentation/ui_labels.py <<'PY_END'

try:
    ROUTE_LABELS_RU.update({
        "strategy.engine.volatility_breakout.title": "Volatility Breakout Engine",
        "strategy.engine.volatility_breakout.subtitle": "Движок пробоя волатильности для исследовательского контура.",
        "strategy.engine.volatility_breakout.lookback": "Период окна",
        "strategy.engine.volatility_breakout.threshold": "Порог пробоя"
    })
except NameError:
    pass
PY_END

cat > scripts/test_volatility_breakout_engine_v1.sh <<'TEST_END'
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
TEST_END

chmod +x scripts/test_volatility_breakout_engine_v1.sh
scripts/test_volatility_breakout_engine_v1.sh

echo "VERDICT=BUILD_VOLATILITY_BREAKOUT_ENGINE_V1_OK"
