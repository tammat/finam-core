#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_strategy_cooldown_builder.py

python - <<'PY'
from datetime import date

from finam_core.runtime.runtime_strategy_cooldown_builder import (
    RuntimeStrategyCooldownBuilder,
)


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.rowcount = 2

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))


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

builder = RuntimeStrategyCooldownBuilder(pg)

affected = builder.build(date(2026, 5, 15))

assert affected == 2
assert pg.conn.commits == 1
assert len(pg.conn.cursor_obj.calls) == 1

sql = pg.conn.cursor_obj.calls[0][0]

assert "strategy_cooldowns" in sql
assert "DISABLE" in sql
assert "REDUCE" in sql

print("OK: runtime strategy cooldown builder")
PY
