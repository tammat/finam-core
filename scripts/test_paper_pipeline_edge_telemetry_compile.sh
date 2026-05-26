#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/edge_execution_gate.py \
  src/finam_core/execution/edge_telemetry.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.pipelines.paper_pipeline import _edge_gate_enrich_payload_for_paper

payload = {
    "symbol": "BRM6@RTSX",
    "strategy": "BR_CONSERVATIVE_BREAKOUT",
    "timeframe": "M5",
}

result = _edge_gate_enrich_payload_for_paper(payload, signal_like=payload)

edge = result["trade_context_snapshot"]["edge_gate"]

assert edge["symbol"] == "BRM6@RTSX"
assert edge["strategy"] == "BR_CONSERVATIVE_BREAKOUT"
assert edge["timeframe"] == "M5"
assert edge["mode"] == "soft"
assert "allowed" in edge
assert "reason" in edge

print("PAPER_PIPELINE_EDGE_TELEMETRY_COMPILE_OK")
PY
