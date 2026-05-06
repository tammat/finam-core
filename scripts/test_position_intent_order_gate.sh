#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_POSITION_INTENT_GATE=1

python - <<'PY'
from dataclasses import dataclass
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


@dataclass
class Policy:
    symbol: str
    horizon: str
    trade_role: str
    allow_intraday_exit: bool
    allow_trailing: bool
    allow_new_buy: bool
    allow_reduce: bool
    allow_increase: bool
    enabled: bool


class DummyRepo:
    def __init__(self, policy):
        self.policy = policy

    def get(self, symbol):
        return self.policy


class DummyPipeline:
    _position_intent_allows_order = PaperTradingPipeline._position_intent_allows_order


# reduce_only: добор long запрещён
p = DummyPipeline()
p.position_intent_repo = DummyRepo(
    Policy("BRM6@RTSX", "intraday", "reduce_only", True, True, False, True, False, True)
)

ok, reason = p._position_intent_allows_order("BRM6@RTSX", "BUY", 2.0)
assert ok is False, (ok, reason)
assert "reduce_only" in reason, reason

# reduce_only: сокращение long разрешено
ok, reason = p._position_intent_allows_order("BRM6@RTSX", "SELL", 2.0)
assert ok is True, (ok, reason)

# watch_only: всё запрещено
p.position_intent_repo = DummyRepo(
    Policy("EUTR@MISX", "long_term", "watch_only", False, False, False, False, False, True)
)

ok, reason = p._position_intent_allows_order("EUTR@MISX", "BUY", 0.0)
assert ok is False, (ok, reason)
assert "watch_only" in reason, reason

# disabled/unknown: запрещено
p.position_intent_repo = DummyRepo(
    Policy("UNKNOWN@MISX", "swing", "watch_only", False, False, False, False, False, False)
)

ok, reason = p._position_intent_allows_order("UNKNOWN@MISX", "BUY", 0.0)
assert ok is False, (ok, reason)

print("POSITION_INTENT_ORDER_GATE_OK")
PY
