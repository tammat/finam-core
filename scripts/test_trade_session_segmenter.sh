#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/trade_session_segmenter.py

python - <<'PY'
from datetime import datetime, timedelta, UTC

from finam_core.analytics.trade_session_segmenter import (
    build_trade_sessions,
)

rows = [
    {
        "id": 1,
        "ts": datetime.now(UTC),
        "strategy": "A",
        "timeframe": "M5",
        "trade_source": "paper",
    },
    {
        "id": 2,
        "ts": datetime.now(UTC) + timedelta(minutes=5),
        "strategy": "A",
        "timeframe": "M5",
        "trade_source": "paper",
    },
    {
        "id": 100,
        "ts": datetime.now(UTC) + timedelta(days=1),
        "strategy": "A",
        "timeframe": "M5",
        "trade_source": "paper",
    },
]

sessions = build_trade_sessions(rows)

assert len(sessions) == 2

print("TRADE_SESSION_SEGMENTER_OK")
PY
