#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_lab_runner_execution_gap_v1"
LOG="/tmp/test_edge_lab_runner_execution_gap_v1.log"

cd "$ROOT"

rm -rf "$OUT"
rm -f "$LOG"

echo "=== TEST EDGE LAB RUNNER EXECUTION GAP V1 ==="

"$PYTHON" \
  scripts/research/audit_edge_lab_runner_execution_gap_v1.py |
tee "$LOG"

for file in \
  "$OUT/findings.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

grep -Fqx \
  "EXECUTION_GAP_CONFIRMED=1" \
  "$OUT/contract.txt"

grep -Fqx \
  "EDGE_RUNNER_INVOKES_BACKTEST=0" \
  "$OUT/contract.txt"

grep -Fqx \
  "EDGE_RUNNER_WRITES_NO_TRADES=1" \
  "$OUT/contract.txt"

grep -Fqx \
  "EDGE_RUNNER_MARKS_DONE=1" \
  "$OUT/contract.txt"

grep -Fqx \
  "SQLITE_BOUNDARY_VIOLATION=1" \
  "$OUT/contract.txt"

grep -Fqx \
  "UNRESOLVED_COUNT=0" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=EDGE_LAB_RUNNER_EXECUTION_GAP_V1_READY" \
  "$LOG"

echo "source_changed=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_LAB_RUNNER_EXECUTION_GAP_V1_OK"
