#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -f sql/create_trade_context_snapshots.sql >/dev/null

python -m py_compile src/finam_core/analytics/trade_context_snapshot_repository.py

python - <<'PY'
import os
from finam_core.analytics.trade_context_snapshot_repository import (
    TradeContextSnapshot,
    TradeContextSnapshotRepository,
)

repo = TradeContextSnapshotRepository(os.environ["DATABASE_URL"])
repo.save(
    TradeContextSnapshot(
        trade_id="test_trade_context_snapshot_v1",
        symbol="BRN6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        side="BUY",
        qty=0.5,
        price=100.0,
        reason="test",
        source="test",
        snapshot={
            "market": {"atr": 0.1},
            "strategy": {"breakout_level": 100.0},
            "risk": {"mode": "test"},
        },
    )
)

print("TRADE_CONTEXT_SNAPSHOT_REPOSITORY_OK")
PY
