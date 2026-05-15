#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/trend_gate_service.py

python - <<'PY'
from finam_core.runtime.trend_gate_service import TrendGateService

svc = TrendGateService()

d = svc.allow_entry(
    symbol="BRM6@RTSX",
    side="BUY",
    expected_side="SELL",
)

assert d.allowed is False
assert "trend_block" in d.reason

d = svc.allow_entry(
    symbol="BRM6@RTSX",
    side="SELL",
    expected_side="SELL",
)

assert d.allowed is True

print("OK: TrendGateService works")
PY
