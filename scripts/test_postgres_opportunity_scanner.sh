#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/moex_opportunity_scanner.py \
  src/finam_core/data/postgres_opportunity_scanner.py

python - <<'PY'
from finam_core.data.postgres_opportunity_scanner import PostgresOpportunityScanner


class Cursor:
    def execute(self, sql):
        assert "market_opportunity_metrics" in sql

    def fetchall(self):
        return [
            ("OZON@MISX", 0.015, 2.0, 2_000_000_000, 0.001, "trend_up_high_vol", 0.75, "INSTITUTIONAL_GRADE"),
            ("SBER@MISX", 0.009, 1.3, 1_000_000_000, 0.001, "trend_up_low_vol", 0.0, "NO_SMART_MONEY_DATA"),
            ("SBER@MISX", 0.020, 3.0, 2_000_000_000, 0.001, "trend_up_high_vol", 0.30, "NORMAL_FLOW"),
            ("TRASH@MISX", 0.02, 3.0, 1_000_000, 0.02, "trend_up_high_vol", 0.0, "NO_SMART_MONEY_DATA"),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Conn:
    def cursor(self):
        return Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class PgLogger:
    def _connect(self):
        return Conn()


scanner = PostgresOpportunityScanner(PgLogger())
items = scanner.top_opportunities(limit=5)

assert len(items) == 2
assert len({x.symbol for x in items}) == 2
assert len(items) == 2
assert len({x.symbol for x in items}) == 2

by_symbol = {x.symbol: x for x in items}

assert "SBER@MISX" in by_symbol
assert "OZON@MISX" in by_symbol

assert by_symbol["SBER@MISX"].smart_money_score >= 0.0
assert by_symbol["OZON@MISX"].smart_money_score == 0.75
assert by_symbol["OZON@MISX"].smart_money_label == "INSTITUTIONAL_GRADE"

assert by_symbol["SBER@MISX"].strategy == "VOLATILITY_BREAKOUT_EQUITY"
assert by_symbol["OZON@MISX"].strategy == "VOLATILITY_BREAKOUT_EQUITY"

print("OK: PostgresOpportunityScanner")
PY
