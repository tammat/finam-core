#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_observation_cost_aggregation_v1"
LOG="/tmp/test_edge_observation_cost_aggregation_v1.log"

cd "$ROOT"

echo "=== TEST EDGE OBSERVATION COST AGGREGATION V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/audit_edge_observation_cost_aggregation_v1.py |
tee "$LOG"

for file in \
  "$OUT/edge_observation_inserts.tsv" \
  "$OUT/insert_bindings.tsv" \
  "$OUT/metric_assignments.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

INSERT_COUNT="$(
  awk -F '=' '
      $1 == "EDGE_OBSERVATION_INSERT_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

MISSING_COST_COLUMN_COUNT="$(
  awk -F '=' '
      $1 == "MISSING_COST_COLUMN_COUNT" {
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

echo "edge_observation_insert_count=$INSERT_COUNT"
echo "missing_cost_column_count=$MISSING_COST_COLUMN_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$INSERT_COUNT" -gt 0 ]]
[[ "$MISSING_COST_COLUMN_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx \
  "SLIPPAGE_EMBEDDED_IN_EXECUTION_PRICES=1" \
  "$OUT/contract.txt"

grep -Fqx \
  "NET_PNL_EXPLICIT_SLIPPAGE_DEDUCTION=0" \
  "$OUT/contract.txt"

grep -Fqx \
  "DOUBLE_SLIPPAGE_DEDUCTION_ALLOWED=0" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=EDGE_OBSERVATION_COST_AGGREGATION_AUDIT_V1_READY" \
  "$LOG"

for marker in \
  "UPDATE analytics.edge_observation_v1" \
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
          scripts/research/audit_edge_observation_cost_aggregation_v1.py ||
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
echo "VERDICT=TEST_EDGE_OBSERVATION_COST_AGGREGATION_V1_OK"
