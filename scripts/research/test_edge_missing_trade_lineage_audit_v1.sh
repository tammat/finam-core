#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_missing_trade_lineage_audit_v1"
LOG="/tmp/test_edge_missing_trade_lineage_audit_v1.log"

cd "$ROOT"

echo "=== TEST EDGE MISSING TRADE LINEAGE AUDIT V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_edge_missing_trade_lineage_audit_v1.py |
tee "$LOG"

for file in \
  "$OUT/missing_trade_runs.tsv" \
  "$OUT/missing_trade_summary.tsv" \
  "$OUT/candidate_priority.tsv" \
  "$OUT/lineage_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

MISSING_COUNT="$(
  tail -n +2 "$OUT/missing_trade_runs.tsv" |
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
  ' "$OUT/missing_trade_summary.tsv"
)"

HIGH_PRIORITY_COUNT="$(
  awk -F '\t' '
      NR > 1 && $1 == "HIGH" {
          count++
      }
      END {
          print count + 0
      }
  ' "$OUT/candidate_priority.tsv"
)"

echo "missing_trade_run_count=$MISSING_COUNT"
echo "summary_count=$SUMMARY_COUNT"
echo "high_priority_count=$HIGH_PRIORITY_COUNT"

[[ "$MISSING_COUNT" -eq 1262 ]]
[[ "$SUMMARY_COUNT" -eq "$MISSING_COUNT" ]]

grep -Fqx "MODE=READ_ONLY" "$OUT/lineage_contract.txt"
grep -Fqx "DATABASE=POSTGRESQL_ONLY" "$OUT/lineage_contract.txt"
grep -Fqx "MISSING_TRADE_RUN_COUNT=1262" "$OUT/lineage_contract.txt"
grep -Fqx "DB_WRITES_PERFORMED=0" "$OUT/lineage_contract.txt"

grep -Fq \
  "VERDICT=EDGE_MISSING_TRADE_LINEAGE_AUDIT_V1_READY" \
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
          scripts/research/build_edge_missing_trade_lineage_audit_v1.py ||
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
echo "VERDICT=TEST_EDGE_MISSING_TRADE_LINEAGE_AUDIT_V1_OK"
