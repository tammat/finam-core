#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src DAILY_LOSS_LIMIT=100 MAX_DRAWDOWN_ABS=200 python - <<'PY'
from finam_core.risk.kill_switch import KillSwitchEngine

e = KillSwitchEngine()

ok = e.evaluate(daily_realized_pnl=-50, equity=99_950, start_equity=100_000)
assert ok.allowed is True

bad_daily = e.evaluate(daily_realized_pnl=-100, equity=99_900, start_equity=100_000)
assert bad_daily.allowed is False
assert bad_daily.reason == "daily_loss_limit_exceeded"
assert bad_daily.kill_switch_active is True

still_blocked = e.evaluate(daily_realized_pnl=0, equity=100_000, start_equity=100_000)
assert still_blocked.allowed is False
assert still_blocked.reason == "kill_switch_active"

e.reset()
bad_dd = e.evaluate(daily_realized_pnl=0, equity=99_800, start_equity=100_000)
assert bad_dd.allowed is False
assert bad_dd.reason == "max_drawdown_exceeded"

print("OK kill_switch")
PY
