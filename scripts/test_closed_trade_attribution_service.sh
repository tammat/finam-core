#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/closed_trade_attribution_service.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from types import SimpleNamespace
from finam_core.analytics.closed_trade_attribution_service import ClosedTradeAttributionService


class Repo:
    def __init__(self):
        self.linked = None
        self.filled = None

    def link_fill(self, **kwargs):
        self.linked = kwargs

    def mark_filled(self, signal_id):
        self.filled = signal_id


repo = Repo()
service = ClosedTradeAttributionService(repo)

fill = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    fill_id="fill-001",
    payload={
        "signal_id": "sig-001",
        "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
    },
)

assert service.link_fill_from_payload(fill) is True
assert repo.linked["signal_id"] == "sig-001"
assert repo.linked["fill_id"] == "fill-001"
assert repo.linked["symbol"] == "BRM6@RTSX"
assert repo.filled == "sig-001"

print("OK: closed trade attribution service links fill from payload")
PY
