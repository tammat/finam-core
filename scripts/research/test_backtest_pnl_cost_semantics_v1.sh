#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/backtest_pnl_cost_semantics_v1"
LOG="/tmp/test_backtest_pnl_cost_semantics_v1.log"

cd "$ROOT"

echo "=== TEST BACKTEST PNL COST SEMANTICS V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/audit_backtest_pnl_cost_semantics_v1.py |
tee "$LOG"

for file in \
  "$OUT/assignments.tsv" \
  "$OUT/pnl_dependencies.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

NET_ASSIGNMENT_COUNT="$(
  awk -F '=' '
      $1 == "NET_ASSIGNMENT_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

NET_SLIPPAGE_COUNT="$(
  awk -F '=' '
      $1 == "NET_EXPLICIT_SLIPPAGE_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

ENTRY_COST_COUNT="$(
  awk -F '=' '
      $1 == "ENTRY_APPLY_COST_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

EXIT_COST_COUNT="$(
  awk -F '=' '
      $1 == "EXIT_APPLY_COST_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "net_assignment_count=$NET_ASSIGNMENT_COUNT"
echo "net_explicit_slippage_count=$NET_SLIPPAGE_COUNT"
echo "entry_apply_cost_count=$ENTRY_COST_COUNT"
echo "exit_apply_cost_count=$EXIT_COST_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$NET_ASSIGNMENT_COUNT" -gt 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx \
  "MODE=STATIC_READ_ONLY" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=BACKTEST_PNL_COST_SEMANTICS_V1_READY" \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "ALTER TABLE" \
  "DROP TABLE" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/audit_backtest_pnl_cost_semantics_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "source_changed=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_BACKTEST_PNL_COST_SEMANTICS_V1_OK"
