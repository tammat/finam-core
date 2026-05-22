#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.manual.manual_trade_journal import ManualTradeRecord

r = ManualTradeRecord(
    symbol="BRM6@RTSX",
    display_name="Фьючерс Brent",
    side="BUY",
    qty=1,
    entry_price=100.0,
    stop_price=99.0,
    take_price=102.0,
    source="manual",
    strategy_reference="br_conservative_breakout",
    confidence=0.75,
    reason="Пробой после сжатия.",
    risk_comment="Портфельный риск повышен.",
    emotion_state="спокойно",
)

assert r.symbol == "BRM6@RTSX"
assert r.confidence == 0.75
assert r.trade_mode == "REAL_MANUAL"

print("TEST_MANUAL_TRADE_JOURNAL_OK")
PY

python -m py_compile \
  src/finam_core/manual/manual_trade_journal.py \
  src/scripts/log_manual_trade.py
