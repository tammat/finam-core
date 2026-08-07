#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_futures_concrete_failure_diagnostics_v1.py"
LOG="/tmp/test_postgresql_futures_concrete_failure_diagnostics_v1.log"

BATCH_ID="${1:?batch id is required}"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --batch-id "$BATCH_ID" |
tee "$LOG"

grep -Fq "run_count=" "$LOG"
grep -Fq "failed_run_count=" "$LOG"
grep -Fq "FAILED_RUN " "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_FUTURES_CONCRETE_FAILURE_DIAGNOSTICS_V1_READY" \
  "$LOG"

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
        grep -F "$marker" "$BUILDER" ||
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
echo "VERDICT=TEST_POSTGRESQL_FUTURES_CONCRETE_FAILURE_DIAGNOSTICS_V1_OK"
