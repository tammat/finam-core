#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_universe_allocator.py \
  src/finam_core/runtime/runtime_allocator_decision_logger.py

python - <<'PY'
from decimal import Decimal

from finam_core.runtime.runtime_universe_allocator import RuntimeUniverseAllocator


class FakeWeightProvider:
    def get_weight(self, *, trade_date, strategy, symbol, timeframe="unknown"):
        return {
            ("GOOD", "SBER@MISX"): Decimal("1.00"),
            ("LIMITED", "LKOH@MISX"): Decimal("1.00"),
            ("BAD", "GAZP@MISX"): Decimal("0.00"),
        }.get((strategy, symbol), Decimal("0.25"))


class FakeDecisionLogger:
    def __init__(self):
        self.decisions = []

    def log_decision(self, **kwargs):
        self.decisions.append(kwargs)


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.rows = [
            ("SBER@MISX", "GOOD", "trend", 10.0, 10, "good", {}),
            ("LKOH@MISX", "LIMITED", "trend", 9.0, 9, "limited", {}),
            ("GAZP@MISX", "BAD", "flat", 100.0, 99, "bad", {}),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (0,)


class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        pass


class FakePg:
    def __init__(self):
        self.conn = FakeConn()

    def _connect(self):
        return self.conn


pg = FakePg()
allocator = RuntimeUniverseAllocator(pg, weight_provider=FakeWeightProvider())
logger = FakeDecisionLogger()
allocator.decision_logger = logger

active_count = allocator.allocate(max_symbols=1, min_score=0.35)

assert active_count == 1

by_symbol = {item["symbol"]: item for item in logger.decisions}

assert by_symbol["SBER@MISX"]["selected"] is True
assert by_symbol["SBER@MISX"]["decision_reason"] == "selected_by_effective_score_limit"

assert by_symbol["LKOH@MISX"]["selected"] is False
assert by_symbol["LKOH@MISX"]["decision_reason"] == "rejected_by_limit"

assert by_symbol["GAZP@MISX"]["selected"] is False
assert by_symbol["GAZP@MISX"]["decision_reason"] == "rejected_by_weight"

print("OK: runtime allocator decision classification")
PY
