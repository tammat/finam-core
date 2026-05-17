#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/strategy_scorecard.py \
  src/finam_core/analytics/strategy_scorecard_persistence.py

python - <<'PY'
from datetime import date

from finam_core.analytics.strategy_scorecard_persistence import StrategyScorecardPersistence


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return [
            ("BRN6@RTSX", "BR_CONSERVATIVE_BREAKOUT", "M5", 100.0, 0.05),
            ("BRN6@RTSX", "BR_CONSERVATIVE_BREAKOUT", "M5", -40.0, 0.05),
        ]


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
    def _connect(self):
        return FakeConn()


persistence = StrategyScorecardPersistence(FakePg())
saved = persistence.calculate_and_save_daily(date(2026, 5, 17))

assert saved == 1

print("OK: strategy scorecard persistence")
PY
