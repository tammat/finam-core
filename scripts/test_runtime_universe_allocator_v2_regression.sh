#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_universe_allocator.py \
  src/finam_core/analytics/strategy_rank_weight_provider.py

python - <<'PY'
from decimal import Decimal

from finam_core.runtime.runtime_universe_allocator import RuntimeUniverseAllocator


class FakeWeightProvider:
    def get_weight(self, *, trade_date, strategy, symbol, timeframe="unknown"):
        weights = {
            ("GOOD", "SBER@MISX"): Decimal("1.00"),
            ("BAD", "GAZP@MISX"): Decimal("0.00"),
            ("WATCH", "LKOH@MISX"): Decimal("0.25"),
        }
        return weights.get((strategy, symbol), Decimal("0.25"))


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.inserted_payloads = []
        self.rows = [
            ("SBER@MISX", "GOOD", "trend", 1.0, 10, "good", {}),
            ("GAZP@MISX", "BAD", "flat", 10.0, 99, "bad", {}),
            ("LKOH@MISX", "WATCH", "trend", 4.0, 50, "watch", {}),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

        if "insert into runtime_active_universe" in sql:
            payload_json = params[-1]
            self.inserted_payloads.append(payload_json)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (0,)


class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


class FakePg:
    def __init__(self):
        self.conn = FakeConn()

    def _connect(self):
        return self.conn


pg = FakePg()

allocator = RuntimeUniverseAllocator(
    pg,
    weight_provider=FakeWeightProvider(),
)

active_count = allocator.allocate(max_symbols=2, min_score=0.35)

assert active_count == 2

insert_calls = [
    item for item in pg.conn.cursor_obj.executed
    if "insert into runtime_active_universe" in item[0]
]

assert len(insert_calls) == 2

inserted_symbols = [call[1][0] for call in insert_calls]
inserted_scores = [float(call[1][3]) for call in insert_calls]

assert inserted_symbols == ["SBER@MISX", "LKOH@MISX"], inserted_symbols
assert inserted_scores == [1.0, 1.0], inserted_scores
assert "GAZP@MISX" not in inserted_symbols

payloads = pg.conn.cursor_obj.inserted_payloads

assert '"base_score": 1.0' in payloads[0]
assert '"strategy_weight": 1.0' in payloads[0]
assert '"effective_score": 1.0' in payloads[0]

assert '"base_score": 4.0' in payloads[1]
assert '"strategy_weight": 0.25' in payloads[1]
assert '"effective_score": 1.0' in payloads[1]

print("OK: RuntimeUniverseAllocator v2 weighted regression")
PY
