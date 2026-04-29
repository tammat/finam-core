#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.signals.strategy_stack import StrategyStack


class NoSignal:
    def on_quote(self, st):
        return None


class BuySignal:
    def on_quote(self, st):
        return {"symbol": st["symbol"], "side": "BUY", "qty": 1, "reason": "test_buy"}


class SellSignal:
    def on_quote(self, st):
        return {"symbol": st["symbol"], "side": "SELL", "qty": 1, "reason": "test_sell"}


st = {"symbol": "BRM6@RTSX", "last": 100}

stack = StrategyStack([NoSignal(), BuySignal(), SellSignal()])
result = stack.collect(st)

assert result.candidates_count == 2
assert result.selected["side"] == "BUY"
assert result.selected["source"] == "BuySignal"
assert result.reason == "selected_first_by_priority"

assert stack.on_quote(st)["side"] == "BUY"

empty = StrategyStack([NoSignal()])
assert empty.collect(st).selected is None

print("OK strategy_stack")
PY
