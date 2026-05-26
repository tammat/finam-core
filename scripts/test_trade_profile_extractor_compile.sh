#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/trade_profile_extractor.py

python - <<'PY'
from finam_core.analytics.trade_profile_extractor import extract_trade_profile_rows

rows = [
    {
        "id": 1,
        "symbol": "BRM6@RTSX",
        "side": "buy",
        "qty": 1,
        "price": 107.55,
        "realized_pnl": 125.0,
        "raw_json": {
            "trade_context_snapshot": {
                "strategy": "br_conservative_breakout",
                "regime": "trend",
                "session": "day",
                "entry_reason": "breakout",
                "exit_reason": "take_profit",
            }
        },
    }
]

profiles = extract_trade_profile_rows(rows)

assert len(profiles) == 1
p = profiles[0]

assert p.trade_id == 1
assert p.symbol == "BRM6@RTSX"
assert p.strategy == "br_conservative_breakout"
assert p.regime == "trend"
assert p.session == "day"
assert p.entry_reason == "breakout"
assert p.exit_reason == "take_profit"
assert p.realized_pnl == 125.0

print("TRADE_PROFILE_EXTRACTOR_OK")
PY
