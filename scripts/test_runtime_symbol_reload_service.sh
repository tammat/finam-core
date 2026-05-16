#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/runtime_symbol_reload_service.py \
  src/finam_core/data/runtime_universe_provider.py

python - <<'PY'
from finam_core.data.runtime_symbol_reload_service import RuntimeSymbolReloadService


class Cursor:
    def execute(self, sql, params):
        assert params == ("opportunity_scanner", 3)

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


svc = RuntimeSymbolReloadService(PgLogger(), limit=3)
d = svc.decide(["BRM6@RTSX"])

assert d.active_symbols == ["BRM6@RTSX", "SBER@MISX", "OZON@MISX"]
assert d.added_symbols == ["SBER@MISX", "OZON@MISX"]
assert d.removed_symbols == []

print("OK: RuntimeSymbolReloadService")
PY
