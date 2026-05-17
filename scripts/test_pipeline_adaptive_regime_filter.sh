#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/risk/adaptive_regime_filter.py \
  src/finam_core/risk/adaptive_regime_repository.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "ENABLE_ADAPTIVE_REGIME_FILTER",
    "AdaptiveRegimeRepository",
    "PIPE_ADAPTIVE_REGIME_FILTER",
    "adaptive_regime_action",
    "adaptive_regime_multiplier",
    "adaptive_regime_reason",
    "_adaptive_regime_filter_if_enabled(intent)",
    "adaptive_regime_adjusted_qty",
]

for c in checks:
    assert c in text, c

flow_pos = text.find("self._inject_latest_institutional_flow_context(intent)")
resolver_pos = text.find("self._resolve_execution_symbol_if_enabled(intent, st)")
regime_pos = text.find("self._adaptive_regime_filter_if_enabled(intent)")
confidence_pos = text.find("_entry_confidence_gate_if_enabled(intent, st)")
sizer_pos = text.find("_adaptive_position_size_if_enabled(intent, st)")

assert flow_pos < resolver_pos < regime_pos < confidence_pos < sizer_pos

print("OK: adaptive regime filter is before confidence gate and sizing")
PY
