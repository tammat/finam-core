#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_cost_model_source_audit_v1"
LOG="/tmp/test_edge_cost_model_source_audit_v1.log"

cd "$ROOT"

echo "=== TEST EDGE COST MODEL SOURCE AUDIT V1 ==="

if [[ ! -f /tmp/edge_cost_recalculation_v1/recalculated_edges.tsv ]]; then
    scripts/research/test_edge_cost_recalculation_v1.sh
fi

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_edge_cost_model_source_audit_v1.py |
tee "$LOG"

for file in \
  "$OUT/source_code_matches.tsv" \
  "$OUT/runner_versions.tsv" \
  "$OUT/source_version_matrix.tsv" \
  "$OUT/mismatch_version_matrix.tsv" \
  "$OUT/audit_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

MISMATCH_TOTAL="$(
  awk -F '\t' '
      NR > 1 {
          total += $6
      }

      END {
          print total + 0
      }
  ' "$OUT/mismatch_version_matrix.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "mismatch_total=$MISMATCH_TOTAL"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$MISMATCH_TOTAL" -eq 476 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx "MODE=READ_ONLY" "$OUT/audit_contract.txt"
grep -Fqx "DATABASE=POSTGRESQL_ONLY" "$OUT/audit_contract.txt"
grep -Fqx "UNRESOLVED_COUNT=0" "$OUT/audit_contract.txt"
grep -Fqx "DB_WRITES_PERFORMED=0" "$OUT/audit_contract.txt"

grep -Fq \
  "VERDICT=EDGE_COST_MODEL_SOURCE_AUDIT_V1_READY" \
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
          scripts/research/build_edge_cost_model_source_audit_v1.py ||
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
echo "VERDICT=TEST_EDGE_COST_MODEL_SOURCE_AUDIT_V1_OK"
