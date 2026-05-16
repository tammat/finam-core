#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_symbol_resolver.py \
  src/scripts/resolve_execution_symbol.py

python - <<'PY'
from finam_core.execution.execution_symbol_resolver import ExecutionSymbolResolver


class Cursor:
    def execute(self, sql, params):
        assert params[0] == "BR_CONT"

    def fetchone(self):
        return ("BRM6@RTSX",)

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


resolver = ExecutionSymbolResolver(PgLogger())

d1 = resolver.resolve("BR_CONT")
assert d1.execution_symbol == "BRM6@RTSX"
assert d1.continuous_symbol == "BR_CONT"

d2 = resolver.resolve("BRN6@RTSX")
assert d2.execution_symbol == "BRM6@RTSX"
assert d2.continuous_symbol == "BR_CONT"

d3 = resolver.resolve("SBER@MISX")
assert d3.execution_symbol == "SBER@MISX"
assert d3.continuous_symbol is None

print("OK: ExecutionSymbolResolver")
PY
