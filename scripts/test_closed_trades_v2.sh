#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/closed_trade_enrichment.py \
  src/scripts/analytics/enrich_closed_trades_v2.py

python - <<'PY'
from finam_core.analytics.closed_trade_enrichment import normalize_root_symbol, calculate_closed_trade_quality

assert normalize_root_symbol("NGM6@RTSX") == "NG"
assert normalize_root_symbol("BRM6@RTSX") == "BR"
assert normalize_root_symbol("USDRUBF@RTSX") == "USDRUB"

q_win = calculate_closed_trade_quality(side="LONG", entry_price=100.0, exit_price=103.0, stop_distance=1.0)
assert q_win.mfe == 3.0
assert q_win.mae == 0.0
assert q_win.realized_rr == 3.0
assert q_win.quality_score == 1.0

q_loss = calculate_closed_trade_quality(side="LONG", entry_price=100.0, exit_price=99.0, stop_distance=1.0)
assert q_loss.mfe == 0.0
assert q_loss.mae == -1.0
assert q_loss.realized_rr == -1.0

print("CLOSED_TRADES_V2_UNIT_OK")
PY

echo "CLOSED_TRADES_V2_TEST_OK"
