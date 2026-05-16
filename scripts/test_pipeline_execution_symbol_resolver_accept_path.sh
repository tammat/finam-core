#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/execution_symbol_resolver.py

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


intent = {
    "symbol": "BRN6@RTSX",
    "qty": 1.0,
    "features": {},
}

market_state = {
    "symbol": "BRN6@RTSX",
}

resolver = ExecutionSymbolResolver(PgLogger())
decision = resolver.resolve(intent["symbol"])

assert decision.requested_symbol == "BRN6@RTSX"
assert decision.execution_symbol == "BRM6@RTSX"
assert decision.continuous_symbol == "BR_CONT"

features = intent.setdefault("features", {})
features["requested_symbol"] = decision.requested_symbol
features["execution_symbol"] = decision.execution_symbol
features["continuous_symbol"] = decision.continuous_symbol
features["execution_symbol_reason"] = decision.reason

intent["requested_symbol"] = decision.requested_symbol
intent["symbol"] = decision.execution_symbol
market_state["requested_symbol"] = decision.requested_symbol
market_state["symbol"] = decision.execution_symbol

assert intent["symbol"] == "BRM6@RTSX"
assert intent["requested_symbol"] == "BRN6@RTSX"
assert market_state["symbol"] == "BRM6@RTSX"
assert market_state["requested_symbol"] == "BRN6@RTSX"

assert intent["features"]["requested_symbol"] == "BRN6@RTSX"
assert intent["features"]["execution_symbol"] == "BRM6@RTSX"
assert intent["features"]["continuous_symbol"] == "BR_CONT"
assert "preferred_symbol_from_liquidity_decision" in intent["features"]["execution_symbol_reason"]

print("OK: pipeline execution symbol resolver ACCEPT path")
PY
