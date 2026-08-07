#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
AUDIT="scripts/research/audit_postgresql_futures_strategy_parameter_contract_v1.py"
LOG="/tmp/test_postgresql_futures_strategy_parameter_contract_v1.log"

BATCH_ID="${1:?failed batch id is required}"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$AUDIT"

set +e

PYTHONPATH=src \
"$PYTHON" "$AUDIT" \
  --strategy-code RSI_MEAN_REVERSION_V1 \
  --failed-batch-id "$BATCH_ID" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "parameter_contract_audit_exit_code=$RC"

grep -Fq "failed_parameter_json=" "$LOG"
grep -Fq "successful_strategy_run_count=" "$LOG"
grep -Fq "root_cause=" "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE analytics" \
  "DELETE FROM analytics" \
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

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

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

if [[ "$RC" -eq 0 ]]; then
    grep -Fq \
      "VERDICT=POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_GAP_CONFIRMED" \
      "$LOG"

    echo \
      "VERDICT=TEST_POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_OK"
    exit 0
fi

grep -Fq \
  "VERDICT=POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_BLOCKED" \
  "$LOG"

echo \
  "VERDICT=TEST_POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_BLOCKED_CONFIRMED"

exit 0
