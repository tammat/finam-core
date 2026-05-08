#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.storage.instrument_spec_repository import InstrumentSpecRepository

calls = []

class FakeCursor:
    def execute(self, sql, params=None):
        calls.append((sql, params))
    def fetchone(self):
        return {
            "symbol": "BRM6@RTSX",
            "base_symbol": "BRM6",
            "asset_class": "FUTURES",
            "min_price_step": 0.01,
            "step_value": 10.0,
            "lot_size": 1.0,
            "currency": "RUB",
            "broker_fee": 1.0,
            "exchange_fee": 1.0,
            "clearing_fee": 0.5,
            "tax_rate": 0.13,
        }
    def fetchall(self):
        return []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class FakeConn:
    def cursor(self, *args, **kwargs):
        return FakeCursor()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

repo = InstrumentSpecRepository(database_url="fake")
repo._connect = lambda: FakeConn()

repo.upsert_spec({
    "symbol": "BRM6@RTSX",
    "base_symbol": "BRM6",
    "asset_class": "FUTURES",
    "min_price_step": 0.01,
    "step_value": 10,
})

row = repo.get_by_symbol("BRM6@RTSX")

assert row["symbol"] == "BRM6@RTSX"
assert "INSERT INTO instrument_specs" in calls[0][0]
assert "SELECT *" in calls[1][0]

print("INSTRUMENT_SPEC_REPOSITORY_OK")
PY
