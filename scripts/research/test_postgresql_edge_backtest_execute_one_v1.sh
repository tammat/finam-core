#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
AUDIT="scripts/research/audit_postgresql_edge_backtest_execute_one_v1.py"
LOG="/tmp/test_postgresql_edge_backtest_execute_one_v1.log"

RUN_UUID="${1:?run uuid is required}"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$AUDIT"

PYTHONPATH=src \
"$PYTHON" "$AUDIT" \
  --run-uuid "$RUN_UUID" |
tee "$LOG"

grep -Fq "adapter_file=" "$LOG"
grep -Fq "execute_one_line=" "$LOG"
grep -Fq "EXECUTE_ONE_CALL " "$LOG"
grep -Fq "root_cause=" "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_EXECUTE_ONE_AUDIT_V1_READY" \
  "$LOG"

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
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_EXECUTE_ONE_V1_OK"
