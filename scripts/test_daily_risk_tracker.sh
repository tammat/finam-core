#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.risk.daily_risk_tracker import DailyRiskTracker

t = DailyRiskTracker()

ok = t.calculate(equities=[100000, 101000, 100500])
assert ok.kill_switch is False, ok
assert ok.daily_pnl == 500.0, ok

loss = t.calculate(equities=[100000, 99000, 96000], max_daily_loss_pct=3.0)
assert loss.kill_switch is True, loss
assert loss.reason == "daily_loss_limit", loss
assert loss.daily_loss_pct == 4.0, loss

dd = t.calculate(equities=[100000, 110000, 98000], max_drawdown_pct=10.0)
assert dd.kill_switch is True, dd
assert dd.reason == "drawdown_limit", dd
assert dd.drawdown_pct == 10.91, dd

empty = t.calculate(equities=[])
assert empty.kill_switch is False, empty
assert empty.reason == "no_equity_data", empty

print("DAILY_RISK_TRACKER_OK")
PY
