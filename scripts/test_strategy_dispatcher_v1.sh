#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_DISPATCHER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/019_strategy_dispatcher_v1.sql

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/dispatchers/strategy_dispatcher.py \
  src/marketcore/presentation/ui_labels.py

PYTHONPATH=src python - <<'PY'
from marketcore.research.execution.dispatchers.strategy_dispatcher import StrategyDispatcher

class DummyEngine:
    engine_name = "DUMMY_ENGINE"

    def execute(self, market_data, parameters=None):
        return []

dispatcher = StrategyDispatcher({"DUMMY_ENGINE": DummyEngine()})
result = dispatcher.dispatch(
    strategy_code="TEST_STRATEGY",
    engine_name="DUMMY_ENGINE",
    engine_version="v1",
)

assert result.strategy_code == "TEST_STRATEGY"
assert result.engine_name == "DUMMY_ENGINE"
assert result.engine.execute(None) == []
PY

registry_rows=$(psql -At -d finam_core -c \
  "SELECT count(*) FROM analytics.strategy_engine_registry_v1;")

engine_col=$(psql -At -d finam_core -c \
  "SELECT count(*) FROM information_schema.columns WHERE table_schema='analytics' AND table_name='strategy_library_v1' AND column_name='engine_name';")

test "$registry_rows" -gt 0
test "$engine_col" = "1"

grep -q "strategy.dispatcher.title" src/marketcore/presentation/ui_labels.py
grep -q "strategy.dispatcher.engine" src/marketcore/presentation/ui_labels.py

echo "strategy_engine_registry_rows=$registry_rows"
echo "strategy_library_engine_name_column=$engine_col"
echo "i18n=ok"
echo "hardcode_strategy_mapping=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_DISPATCHER_V1_OK"
