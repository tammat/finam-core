#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/control/adaptive_strategy_controller.py \
  src/scripts/run_strategy_performance_monitor.py

python - <<'PY'
from finam_core.control.adaptive_strategy_controller import AdaptiveStrategyController

class FakeConn:
    def cursor(self):
        raise RuntimeError("db_not_used")

c = AdaptiveStrategyController(FakeConn())

assert c.classify_metrics(trades=5, profit_factor=10, expectancy=1)[0] == "NO_DATA"
assert c.classify_metrics(trades=20, profit_factor=2, expectancy=1)[0] == "HEALTHY"
assert c.classify_metrics(trades=20, profit_factor=1.2, expectancy=0.1)[0] == "WATCH"
assert c.classify_metrics(trades=20, profit_factor=0.8, expectancy=-0.1)[0] == "DEGRADED"
assert c.classify_metrics(trades=20, profit_factor=0.0, expectancy=-2000, net_pnl=-10000)[0] == "BLOCKED"

print("OK: adaptive strategy controller v2 rules passed")
PY
