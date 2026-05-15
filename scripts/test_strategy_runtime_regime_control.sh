#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/regime_runtime_control_service.py

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/create_strategy_runtime_regime_control.sql >/dev/null

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -P pager=off -c "
insert into strategy_runtime_regime_control (
  symbol, strategy, regime, status, allow_trade, watch_only, risk_multiplier, reason, updated_at
)
values (
  'BR_CONT',
  'BR_CONSERVATIVE_BREAKOUT',
  'trend_up_high_vol',
  'BLOCKED',
  false,
  true,
  0,
  'test_regime_failure_zone',
  now()
)
on conflict (symbol, strategy, regime) do update set
  status = excluded.status,
  allow_trade = excluded.allow_trade,
  watch_only = excluded.watch_only,
  risk_multiplier = excluded.risk_multiplier,
  reason = excluded.reason,
  updated_at = now();
"

python - <<'PY'
from finam_core.runtime.regime_runtime_control_service import RegimeRuntimeControlService
from finam_core.storage.postgres_logger import PostgresLogger

svc = RegimeRuntimeControlService(PostgresLogger())

allowed, qty, reason = svc.allow_regime(
    symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    regime="trend_up_high_vol",
    qty=1.0,
)

assert allowed is False
assert qty == 0.0
assert "regime_control_blocked" in reason
assert "trend_up_high_vol" in reason

print("OK: strategy runtime regime control blocks bad regime")
PY
