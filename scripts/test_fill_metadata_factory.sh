#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/fill_metadata_factory.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from types import SimpleNamespace

from finam_core.execution.fill_metadata_factory import FillMetadataFactory

intent = {
    "signal_id": "sig-001",
    "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
    "horizon": "INTRADAY",
    "timeframe": "M5",
}
market_state = {"regime": "trend_high_vol"}
raw_fill = SimpleNamespace(payload={"paper_only": True})
fill = SimpleNamespace(symbol="BRM6@RTSX", side="BUY", qty=1, price=100)

FillMetadataFactory.attach(fill, intent=intent, market_state=market_state, raw_fill=raw_fill)

assert fill.signal_id == "sig-001"
assert fill.payload["signal_id"] == "sig-001"
assert fill.payload["strategy"] == "BR_CONSERVATIVE_BREAKOUT_M5"
assert fill.payload["horizon"] == "INTRADAY"
assert fill.payload["regime"] == "trend_high_vol"
assert fill.payload["timeframe"] == "M5"
assert fill.payload["paper_only"] is True

print("OK: fill metadata factory")
PY

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.execution.fill_metadata_factory import FillMetadataFactory" in text
assert "FillMetadataFactory.attach(fill, intent=intent, market_state=st, raw_fill=raw_fill)" in text
assert "PIPE_FILL_METADATA_ATTACH_FAILED" not in text

print("OK: paper_pipeline uses FillMetadataFactory")
PY
