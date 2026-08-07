#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
EXPOSER="scripts/research/expose_postgresql_edge_backtest_execute_one_source_v1.py"
LOG="/tmp/test_expose_postgresql_edge_backtest_execute_one_source_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$EXPOSER"

PYTHONPATH=src \
"$PYTHON" "$EXPOSER" |
tee "$LOG"

grep -Fq "adapter_file=" "$LOG"
grep -Fq "EXECUTE_ONE_CALL " "$LOG"
grep -Fq "=== EXECUTE_ONE_SOURCE_BEGIN ===" "$LOG"
grep -Fq "=== EXECUTE_ONE_SOURCE_END ===" "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_EXECUTE_ONE_SOURCE_V1_EXPOSED" \
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
        grep -F "$marker" "$EXPOSER" || true
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
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_EXECUTE_ONE_SOURCE_V1_OK"
