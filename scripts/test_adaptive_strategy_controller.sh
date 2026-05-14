#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/control/adaptive_strategy_controller.py

python - <<'PY'
from finam_core.control.adaptive_strategy_controller import AdaptiveStrategyController

class FakeConn:
    def cursor(self):
        raise RuntimeError("db_not_used_in_unit_test")

c = AdaptiveStrategyController(FakeConn())

healthy = c.decision_from_status("BRM6@RTSX", "HEALTHY")
assert healthy.allow_trade is True
assert healthy.watch_only is False
assert healthy.risk_multiplier == 1.0

watch = c.decision_from_status("BRM6@RTSX", "WATCH")
assert watch.allow_trade is True
assert watch.risk_multiplier == 0.5

degraded = c.decision_from_status("BRM6@RTSX", "DEGRADED")
assert degraded.allow_trade is False
assert degraded.watch_only is True

nodata = c.decision_from_status("BRM6@RTSX", "NO_DATA")
assert nodata.allow_trade is False
assert nodata.risk_multiplier == 0.0

print("OK: adaptive strategy controller unit rules passed")
PY
