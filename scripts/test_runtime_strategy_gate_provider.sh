#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/runtime_strategy_gate_provider.py

python - <<'PY'
from datetime import date

from finam_core.runtime.runtime_strategy_gate_provider import RuntimeStrategyGateProvider


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.params = params

    def fetchone(self):
        return self.row


class FakeConn:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return FakeCursor(self.row)


class FakePg:
    def __init__(self, row):
        self.row = row

    def _connect(self):
        return FakeConn(self.row)


trade_date = date(2026, 5, 15)

allowed, reason = RuntimeStrategyGateProvider(FakePg(("ENABLE", "ok"))).allows(
    trade_date=trade_date,
    strategy="BR_CONSERVATIVE_BREAKOUT",
    symbol="BRM6@RTSX",
    timeframe="INTRADAY",
)
assert allowed is True
assert "allowed:ENABLE" in reason

allowed, reason = RuntimeStrategyGateProvider(FakePg(("DISABLE", "bad"))).allows(
    trade_date=trade_date,
    strategy="USDRUB_REGIME",
    symbol="USDRUBF@RTSX",
)
assert allowed is False
assert "blocked:DISABLE" in reason

allowed, reason = RuntimeStrategyGateProvider(FakePg(None)).allows(
    trade_date=trade_date,
    strategy="NEW",
    symbol="SBER@MISX",
)
assert allowed is True
assert reason == "runtime_strategy_gate_no_rank_decision"

print("OK: runtime strategy gate provider")
PY
