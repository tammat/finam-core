#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/fill_persistence_service.py

python - <<'PY'
from types import SimpleNamespace

from finam_core.execution.fill_persistence_service import FillPersistenceService


class PgLogger:
    def __init__(self):
        self.kwargs = None

    def log_fill(self, **kwargs):
        self.kwargs = kwargs


class Attribution:
    def __init__(self):
        self.fill = None

    def link_fill_from_payload(self, fill):
        self.fill = fill
        return True


pg = PgLogger()
attr = Attribution()

fill = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1.0,
    price=100.0,
    commission=0.1,
    fill_id="fill-001",
    signal_id="sig-001",
    payload={
        "signal_id": "sig-001",
        "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
    },
)

service = FillPersistenceService(pg_logger=pg, attribution_service=attr)
result = service.persist_fill(fill, execution_type="paper")

assert result["fill_logged"] is True
assert result["signal_linked"] is True
assert result["fill_id"] == "fill-001"
assert result["signal_id"] == "sig-001"

assert pg.kwargs["symbol"] == "BRM6@RTSX"
assert pg.kwargs["trade_id"] == "fill-001"
assert pg.kwargs["payload"]["signal_id"] == "sig-001"
assert attr.fill is fill

print("OK: сервис сохранения fill работает")
PY
