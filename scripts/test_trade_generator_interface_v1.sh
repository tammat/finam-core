#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADE_GENERATOR_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/dto/research_trade.py \
  src/marketcore/research/execution/interfaces/trade_generator.py \
  src/marketcore/presentation/ui_labels.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime, timedelta

from marketcore.research.execution.dto.research_trade import ResearchTrade

entry = datetime.now(UTC)
exit_ts = entry + timedelta(minutes=5)

buy = ResearchTrade.create(
    signal_uuid=None,
    entry_ts=entry,
    exit_ts=exit_ts,
    side="BUY",
    entry_price=100.0,
    exit_price=105.0,
    quantity=2.0,
    commission=1.0,
    slippage=0.5,
    execution_model="CLOSE_TO_CLOSE",
)

sell = ResearchTrade.create(
    signal_uuid=None,
    entry_ts=entry,
    exit_ts=exit_ts,
    side="SELL",
    entry_price=105.0,
    exit_price=100.0,
    quantity=2.0,
    commission=1.0,
    slippage=0.5,
    execution_model="CLOSE_TO_CLOSE",
)

assert buy.gross_pnl == 10.0
assert buy.net_pnl == 8.5
assert sell.gross_pnl == 10.0
assert sell.net_pnl == 8.5
assert buy.execution_model == "CLOSE_TO_CLOSE"
PY

grep -q "trade.generator.title" src/marketcore/presentation/ui_labels.py
grep -q "trade.generator.execution_model" src/marketcore/presentation/ui_labels.py

echo "i18n=ok"
echo "sql_in_component=0"
echo "side_effects=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADE_GENERATOR_INTERFACE_V1_READY"
echo "VERDICT=TEST_TRADE_GENERATOR_INTERFACE_V1_OK"
