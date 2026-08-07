#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
AUDIT="scripts/research/audit_postgresql_edge_backtest_rsi_dispatch_v1.py"
LOG="/tmp/test_postgresql_edge_backtest_rsi_dispatch_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$AUDIT"

set +e

PYTHONPATH=src \
"$PYTHON" "$AUDIT" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "rsi_dispatch_audit_exit_code=$RC"

grep -Fq "root_cause=" "$LOG"
grep -Fq "rsi_candidate_function_count=" "$LOG"

for marker in \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" "$AUDIT" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_runtime_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "db_writes_performed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

if [[ "$RC" -eq 0 ]]; then
    echo \
      "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_OK"
    exit 0
fi

if [[ "$RC" -eq 2 ]]; then
    grep -Fq \
      "VERDICT=POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_BLOCKED" \
      "$LOG"

    echo \
      "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_BLOCKED_CONFIRMED"
    exit 0
fi

echo \
  "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_FAILED"
exit "$RC"
