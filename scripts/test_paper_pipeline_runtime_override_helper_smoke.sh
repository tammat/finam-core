#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=paper

python - <<'PY'
from types import SimpleNamespace

from finam_core.pipelines.paper_pipeline import PaperTradingPipeline

pipe = object.__new__(PaperTradingPipeline)

signal = SimpleNamespace(
    symbol="BRM6@RTSX",
    timeframe="M5",
    payload={"timeframe": "M5"},
)

allowed, qty, reason = pipe._runtime_override_gate_allows_paper_signal(
    br_signal=signal,
    qty=1.0,
    strategy="BR_CONSERVATIVE_BREAKOUT",
)

assert allowed is False
assert qty == 0.0
assert "runtime_override_block" in reason

signal_live = SimpleNamespace(
    symbol="BRM6@RTSX",
    timeframe="LIVE",
    payload={"timeframe": "LIVE"},
)

allowed, qty, reason = pipe._runtime_override_gate_allows_paper_signal(
    br_signal=signal_live,
    qty=1.0,
    strategy="BR_CONSERVATIVE_BREAKOUT",
)

assert allowed is True
assert qty == 0.5
assert "runtime_override_applied" in reason

print("PAPER_PIPELINE_RUNTIME_OVERRIDE_HELPER_SMOKE_OK")
PY
