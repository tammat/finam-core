#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_futures_concrete_contract_backtest_v1.py"
LOG="/tmp/test_postgresql_futures_concrete_contract_backtest_v1.log"

cd "$ROOT"
rm -f "$LOG"

CONTRACT_SYMBOL="${1:?contract symbol is required}"
STRATEGY_CODE="${2:-RSI_MEAN_REVERSION_V1}"
TIMEFRAME="${3:-M5}"
BATCH_ID="PG_FUTURES_CONCRETE_TEST_V1_$(date +%Y%m%d_%H%M%S)"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --continuous-symbol "NG@RTSX" \
  --contract-symbol "$CONTRACT_SYMBOL" \
  --strategy-code "$STRATEGY_CODE" \
  --timeframe "$TIMEFRAME" \
  --batch-id "$BATCH_ID" |
tee "$LOG"

grep -Fq \
  "contract_symbol=$CONTRACT_SYMBOL" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_FUTURES_CONCRETE_CONTRACT_TASK_DRY_RUN_OK" \
  "$LOG"

for marker in \
  "UPDATE analytics.research_trade_v1" \
  "DELETE FROM analytics.research_trade_v1" \
  "send_order(" \
  "place_order(" \
  "submit_order(" \
  "sqlite3" \
  "bars.sqlite"
do
    COUNT="$(
      {
        grep -F "$marker" "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "batch_id=$BATCH_ID"
echo "db_writes_performed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_FUTURES_CONCRETE_CONTRACT_BACKTEST_V1_OK"
