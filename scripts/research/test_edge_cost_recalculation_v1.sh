#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_cost_recalculation_v1"
LOG="/tmp/test_edge_cost_recalculation_v1.log"

cd "$ROOT"

echo "=== TEST EDGE COST RECALCULATION V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_edge_cost_recalculation_v1.py |
tee "$LOG"

for file in \
  "$OUT/recalculated_edges.tsv" \
  "$OUT/reconciliation_summary.tsv" \
  "$OUT/validated_candidates.tsv" \
  "$OUT/rejected_candidates.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

SAFE_SOURCE_COUNT="$(
  tail -n +2 "$OUT/recalculated_edges.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

VALIDATED_COUNT="$(
  tail -n +2 "$OUT/validated_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

REJECTED_COUNT="$(
  tail -n +2 "$OUT/rejected_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

SUMMARY_COUNT="$(
  awk -F '\t' '
      NR > 1 {
          total += $2
      }

      END {
          print total + 0
      }
  ' "$OUT/reconciliation_summary.tsv"
)"

echo "safe_source_count=$SAFE_SOURCE_COUNT"
echo "cost_validated_count=$VALIDATED_COUNT"
echo "rejected_count=$REJECTED_COUNT"
echo "summary_count=$SUMMARY_COUNT"

[[ "$SAFE_SOURCE_COUNT" -eq 489 ]]
[[ "$SUMMARY_COUNT" -eq "$SAFE_SOURCE_COUNT" ]]
[[ "$((VALIDATED_COUNT + REJECTED_COUNT))" -eq "$SAFE_SOURCE_COUNT" ]]

grep -Fqx "MODE=READ_ONLY" "$OUT/contract.txt"
grep -Fqx "DATABASE=POSTGRESQL_ONLY" "$OUT/contract.txt"
grep -Fqx "SAFE_SOURCE_COUNT=489" "$OUT/contract.txt"
grep -Fqx "MINIMUM_TRADES=30" "$OUT/contract.txt"
grep -Fqx "DB_WRITES_PERFORMED=0" "$OUT/contract.txt"

grep -Fq \
  "VERDICT=EDGE_COST_RECALCULATION_V1_READY" \
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
          scripts/research/build_edge_cost_recalculation_v1.py ||
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
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_COST_RECALCULATION_V1_OK"
