#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/data/runtime_universe_provider.py

python - <<'PY'
from finam_core.data.runtime_universe_provider import RuntimeUniverseProvider


class Cursor:
    def execute(self, sql, params):
        assert "dynamic_watchlist" in sql
        assert params == ("opportunity_scanner", 2)

    def fetchall(self):
        return [("SBER@MISX",), ("OZON@MISX",)]

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


items = RuntimeUniverseProvider(PgLogger()).load_symbols(limit=2)

assert items == ["SBER@MISX", "OZON@MISX"]

print("OK: RuntimeUniverseProvider")
PY
