#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/edge_validation.py \
  src/finam_core/analytics/trade_pnl_reconstructor.py \
  src/finam_core/analytics/trade_session_segmenter.py \
  src/finam_core/analytics/session_edge_builder.py

python - <<'PY'
from datetime import datetime, timedelta, UTC

from finam_core.analytics.session_edge_builder import build_session_edge_results

t0 = datetime.now(UTC)

rows = [
    {
        "id": 1,
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "price": 100.0,
        "commission": 0.0,
        "ts": t0,
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "timeframe": "M5",
        "trade_source": "paper",
    },
    {
        "id": 2,
        "symbol": "BRM6@RTSX",
        "side": "SELL",
        "qty": 1,
        "price": 105.0,
        "commission": 0.0,
        "ts": t0 + timedelta(minutes=5),
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "timeframe": "M5",
        "trade_source": "paper",
    },
    {
        "id": 100,
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "price": 110.0,
        "commission": 0.0,
        "ts": t0 + timedelta(days=1),
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "timeframe": "M5",
        "trade_source": "paper",
    },
    {
        "id": 101,
        "symbol": "BRM6@RTSX",
        "side": "SELL",
        "qty": 1,
        "price": 108.0,
        "commission": 0.0,
        "ts": t0 + timedelta(days=1, minutes=5),
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "timeframe": "M5",
        "trade_source": "paper",
    },
]

results = build_session_edge_results(rows)

assert len(results) == 2
assert results[0].bucket.trades == 1
assert results[0].bucket.gross_pnl == 5.0
assert results[1].bucket.trades == 1
assert results[1].bucket.gross_pnl == -2.0

print("SESSION_EDGE_BUILDER_OK")
PY
