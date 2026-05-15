#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/signals/signal_intent.py \
  src/finam_core/signals/strategy_intent_adapter.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.signals.strategy_intent_adapter import StrategyIntentAdapter" in text
assert "SIGNAL INTENT V2 COMPATIBILITY BRIDGE" in text
assert "StrategyIntentAdapter.normalize(raw_intent)" in text
assert "StrategyIntentAdapter.to_pipeline_dict(normalized_signal_intent)" in text
assert "PIPE_SIGNAL_INTENT_ADAPTER_ERROR" in text

bridge_pos = text.find("SIGNAL INTENT V2 COMPATIBILITY BRIDGE")
router_pos = text.find("routed = self.signal_intent_router.route(raw_intent)", bridge_pos)

assert bridge_pos != -1
assert router_pos != -1
assert bridge_pos < router_pos

print("OK: pipeline SignalIntent adapter bridge is before router")
PY
