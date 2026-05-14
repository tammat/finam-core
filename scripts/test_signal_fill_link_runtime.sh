#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/signal_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from types import SimpleNamespace

intent = {
    "signal_id": "sig-test-001",
    "strategy": "TEST_STRATEGY",
    "horizon": "INTRADAY",
    "regime": "trend_high_vol",
    "timeframe": "M5",
}

st = {"regime": "trend_high_vol", "regime_trend": "up"}

raw_fill = SimpleNamespace(
    fill_id="fill-test-001",
    payload={"paper_only": True},
)

fill = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    commission=0.1,
    fill_id=raw_fill.fill_id,
)

signal_payload = {
    "signal_id": intent.get("signal_id"),
    "strategy": intent.get("strategy") or (intent.get("features") or {}).get("strategy"),
    "horizon": intent.get("horizon") or intent.get("signal_horizon"),
    "regime": intent.get("regime") or st.get("regime") or st.get("regime_trend"),
    "timeframe": intent.get("timeframe"),
}

fill.signal_id = signal_payload.get("signal_id")
fill.payload = {
    **(getattr(raw_fill, "payload", {}) if isinstance(getattr(raw_fill, "payload", None), dict) else {}),
    **{k: v for k, v in signal_payload.items() if v is not None},
}

assert fill.signal_id == "sig-test-001"
assert fill.payload["signal_id"] == "sig-test-001"
assert fill.payload["strategy"] == "TEST_STRATEGY"
assert fill.payload["horizon"] == "INTRADAY"
assert fill.payload["regime"] == "trend_high_vol"
assert fill.payload["timeframe"] == "M5"
assert fill.payload["paper_only"] is True

print("OK: signal metadata can be attached to paper fill runtime")
PY
