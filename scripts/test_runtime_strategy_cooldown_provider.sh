#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/runtime_strategy_cooldown_provider.py

python - <<'PY'
from finam_core.runtime.runtime_strategy_cooldown_provider import RuntimeStrategyCooldownProvider


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


allowed, reason = RuntimeStrategyCooldownProvider(FakePg(None)).allows(
    strategy="BR_CONSERVATIVE_BREAKOUT",
    symbol="BRM6@RTSX",
    timeframe="INTRADAY",
)

assert allowed is True
assert reason == "runtime_strategy_cooldown_not_active"

allowed, reason = RuntimeStrategyCooldownProvider(
    FakePg(("DISABLE", "negative_expectancy", "2026-05-19 00:00:00+00"))
).allows(
    strategy="USDRUB_REGIME",
    symbol="USDRUBF@RTSX",
)

assert allowed is False
assert "runtime_strategy_cooldown_active" in reason
assert "negative_expectancy" in reason

print("OK: runtime strategy cooldown provider")
PY
