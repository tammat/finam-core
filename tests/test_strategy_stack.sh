#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.signals.strategy_stack import StrategyStack


class NoSignal:
    def on_quote(self, st):
        return None


class LowConfidenceBuy:
    def on_quote(self, st):
        return {
            "symbol": st["symbol"],
            "side": "BUY",
            "qty": 1,
            "confidence": 0.4,
            "score": 0.4,
            "reason": "low_buy",
        }


class HighConfidenceSell:
    def on_quote(self, st):
        return {
            "symbol": st["symbol"],
            "side": "SELL",
            "qty": 1,
            "confidence": 0.9,
            "score": 0.9,
            "reason": "high_sell",
        }


class SameConfidenceHigherScore:
    def on_quote(self, st):
        return {
            "symbol": st["symbol"],
            "side": "BUY",
            "qty": 1,
            "confidence": 0.9,
            "score": 1.2,
            "reason": "better_score",
        }


st = {"symbol": "BRM6@RTSX", "last": 100}

stack = StrategyStack([NoSignal(), LowConfidenceBuy(), HighConfidenceSell()])
result = stack.collect(st)

assert result.candidates_count == 2
assert result.selected["side"] == "SELL"
assert result.selected["source"] == "HighConfidenceSell"
assert result.reason == "selected_by_score"

stack2 = StrategyStack([HighConfidenceSell(), SameConfidenceHigherScore()])
result2 = stack2.collect(st)

assert result2.candidates_count == 2
assert result2.selected["side"] == "BUY"
assert result2.selected["source"] == "SameConfidenceHigherScore"

empty = StrategyStack([NoSignal()])
assert empty.collect(st).selected is None

print("OK strategy_stack")
PY
