#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
AUDIT="scripts/research/audit_sber_cost_replay_quantity_semantics_v1.py"

BATCH_ID="${1:-PG_EDGE_FAMILY_EXPANSION_V1_20260806_073217}"
LOG="/tmp/test_sber_cost_replay_quantity_semantics_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$AUDIT"

set +e

PYTHONPATH=src \
"$PYTHON" "$AUDIT" \
  --batch-id "$BATCH_ID" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "quantity_semantics_exit_code=$RC"

grep -Fq "source_run_uuid=" "$LOG"
grep -Fq "configured_quantity=" "$LOG"
grep -Fq "median_implied_quantity=" "$LOG"
grep -Fq "pnl_quantity_semantics=" "$LOG"
grep -Fq "executable_lot_replay_ready=" "$LOG"

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
      "VERDICT=SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_READY" \
      "$LOG"

    echo "VERDICT=TEST_SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_READY"
    exit 0
fi

if [[ "$RC" -eq 2 ]]; then
    grep -Fq \
      "VERDICT=SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_BLOCKED" \
      "$LOG"

    echo "VERDICT=TEST_SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_BLOCKED_CORRECTLY"
    exit 0
fi

echo "VERDICT=TEST_SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_FAILED"
exit "$RC"
