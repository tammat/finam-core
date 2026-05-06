#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHONPATH=src .venv/bin/python - <<'PY'
from finam_core.strategy.br_regime_layer import BRRegimeDecision
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


d = BRRegimeDecision(
    allowed=True,
    regime="compression",
    reason="confirmation_required",
    size_multiplier=0.5,
    confirmation_required=True,
)

assert d.confirmation_required is True
print("BR_CONFIRM_PENDING_OK")


class DummyPipeline:
    def __init__(self):
        self._br_confirm_pending = {
            "BRM6@RTSX": {
                "side": "BUY",
                "level": 110.0,
                "ticks": 0,
            }
        }


pipe = DummyPipeline()
check = PaperTradingPipeline._check_br_confirmation

assert check(pipe, "BRM6@RTSX", "BUY", 110.01) is False
assert check(pipe, "BRM6@RTSX", "BUY", 110.02) is False
assert check(pipe, "BRM6@RTSX", "BUY", 110.03) is True
assert "BRM6@RTSX" not in pipe._br_confirm_pending
print("BR_CONFIRM_TRIGGER_OK")


pipe = DummyPipeline()
assert check(pipe, "BRM6@RTSX", "BUY", 109.99) is False
assert "BRM6@RTSX" not in pipe._br_confirm_pending
print("BR_CONFIRM_REJECT_OK")
PY
