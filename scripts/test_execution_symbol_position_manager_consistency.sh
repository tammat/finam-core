#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/accounting/position_manager.py \
  src/finam_core/execution/execution_symbol_resolver.py

python - <<'PY'
from dataclasses import dataclass

from finam_core.accounting.position_manager import PositionManager
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


@dataclass
class Fill:
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0
    fill_id: str | None = None
    payload: dict | None = None


resolver = ExecutionSymbolResolver(PgLogger())
decision = resolver.resolve("BRN6@RTSX")

assert decision.requested_symbol == "BRN6@RTSX"
assert decision.execution_symbol == "BRM6@RTSX"

pm = PositionManager(starting_cash=100000.0)

fill = Fill(
    symbol=decision.execution_symbol,
    side="BUY",
    qty=1,
    price=110.0,
    fill_id="resolver-test-fill",
    payload={
        "requested_symbol": decision.requested_symbol,
        "execution_symbol": decision.execution_symbol,
        "continuous_symbol": decision.continuous_symbol,
        "execution_symbol_reason": decision.reason,
    },
)

pm.apply_fill(fill)

assert "BRM6@RTSX" in pm.positions
assert pm.positions["BRM6@RTSX"].qty == 1.0

assert "BRN6@RTSX" not in pm.positions or pm.positions["BRN6@RTSX"].qty == 0.0

print("OK: execution symbol is authoritative for PositionManager")
PY
