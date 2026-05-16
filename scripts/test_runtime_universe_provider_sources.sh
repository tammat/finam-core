#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/runtime_universe_provider.py \
  src/finam_core/data/runtime_symbol_reload_service.py

python - <<'PY'
from finam_core.data.runtime_symbol_reload_service import RuntimeSymbolReloadService


class Cursor:
    def execute(self, sql, params):
        sources, limit = params
        assert "opportunity_scanner" in sources
        assert "confirmation_universe" in sources
        assert limit == 5

    def fetchall(self):
        return [
            ("BRM6@RTSX",),
            ("BRN6@RTSX",),
            ("SBER@MISX",),
            ("OZON@MISX",),
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


svc = RuntimeSymbolReloadService(PgLogger(), limit=5)
d = svc.decide(["BRM6@RTSX"])

assert "BRM6@RTSX" in d.active_symbols
assert "BRN6@RTSX" in d.active_symbols
assert "SBER@MISX" in d.active_symbols
assert "OZON@MISX" in d.active_symbols

print("OK: runtime universe includes confirmation sources")
PY
