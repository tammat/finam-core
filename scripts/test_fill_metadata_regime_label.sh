#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/fill_metadata_factory.py

python - <<'PY'
from finam_core.execution.fill_metadata_factory import FillMetadataFactory

payload = FillMetadataFactory.build(
    intent={
        "symbol": "BRM6@RTSX",
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "confidence": 0.77,
        "features": {"regime_label": "trend_up_high_vol"},
    },
    market_state={},
    raw_payload={},
)

assert payload["regime"] == "trend_up_high_vol"
assert payload["regime_label"] == "trend_up_high_vol"
assert payload["confidence"] == 0.77
assert payload["continuous_symbol"] == "BR_CONT"

print("OK: FillMetadataFactory enriches regime_label/confidence")
PY
