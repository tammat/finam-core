#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from datetime import date

from finam_core.futures.futures_access_gate import FuturesAccessGate

gate_before = FuturesAccessGate(today=date(2026, 5, 10))

d1 = gate_before.check(symbol="BRM6@RTSX", execution_mode="real")
assert d1.allowed is False, d1
assert "blocked_until_2026-07-01" in d1.reason, d1

d2 = gate_before.check(symbol="BRM6@RTSX", execution_mode="real_dry_run")
assert d2.allowed is True, d2

d3 = gate_before.check(symbol="SBER@MISX", execution_mode="real")
assert d3.allowed is True, d3

gate_after = FuturesAccessGate(today=date(2026, 7, 2))

d4 = gate_after.check(symbol="BRM6@RTSX", execution_mode="real")
assert d4.allowed is False, d4
assert d4.reason == "ENABLE_REAL_FUTURES_TRADING_not_enabled", d4

print("FUTURES_ACCESS_GATE_OK")
PY
