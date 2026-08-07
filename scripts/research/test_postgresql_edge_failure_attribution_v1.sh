#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_edge_failure_attribution_v1.py"

BATCH_ID="${1:-PG_EDGE_FAMILY_EXPANSION_V1_20260806_073217}"

OUT="/tmp/postgresql_edge_failure_attribution_v1/$BATCH_ID"
LOG="/tmp/test_postgresql_edge_failure_attribution_v1.log"

cd "$ROOT"

echo "=== TEST POSTGRESQL EDGE FAILURE ATTRIBUTION V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

set +e

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --batch-id "$BATCH_ID" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "builder_exit_code=$RC"

for file in \
  "$OUT/batch_summary.tsv" \
  "$OUT/run_attribution.tsv" \
  "$OUT/family_symbol_attribution.tsv" \
  "$OUT/side_attribution.tsv" \
  "$OUT/entry_hour_attribution.tsv" \
  "$OUT/hold_duration_attribution.tsv" \
  "$OUT/excursion_attribution.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

TOTAL_RUN_COUNT="$(
  awk -F= '
      $1 == "TOTAL_RUN_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

DONE_RUN_COUNT="$(
  awk -F= '
      $1 == "DONE_RUN_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

TRADE_ROW_COUNT="$(
  awk -F= '
      $1 == "TRADE_ROW_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

ATTRIBUTED_TRADE_COUNT="$(
  awk -F= '
      $1 == "ATTRIBUTED_TRADE_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

GROUP_COUNT="$(
  awk -F= '
      $1 == "FAMILY_SYMBOL_GROUP_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

UNRESOLVED_COUNT="$(
  awk -F= '
      $1 == "UNRESOLVED_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

echo "total_run_count=$TOTAL_RUN_COUNT"
echo "done_run_count=$DONE_RUN_COUNT"
echo "trade_row_count=$TRADE_ROW_COUNT"
echo "attributed_trade_count=$ATTRIBUTED_TRADE_COUNT"
echo "family_symbol_group_count=$GROUP_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$TOTAL_RUN_COUNT" -eq 96 ]]
[[ "$DONE_RUN_COUNT" -eq 96 ]]
[[ "$TRADE_ROW_COUNT" -gt 0 ]]
[[ "$ATTRIBUTED_TRADE_COUNT" -eq "$TRADE_ROW_COUNT" ]]
[[ "$GROUP_COUNT" -eq 6 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]
[[ "$RC" -eq 0 ]]

FAMILY_ROWS="$(
  tail -n +2 "$OUT/family_symbol_attribution.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

SIDE_ROWS="$(
  tail -n +2 "$OUT/side_attribution.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

HOUR_ROWS="$(
  tail -n +2 "$OUT/entry_hour_attribution.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

[[ "$FAMILY_ROWS" -eq 6 ]]
[[ "$SIDE_ROWS" -gt 0 ]]
[[ "$HOUR_ROWS" -gt 0 ]]

grep -Fqx \
  "DATABASE=POSTGRESQL_ONLY" \
  "$OUT/contract.txt"

grep -Fqx \
  "DB_WRITES_PERFORMED=0" \
  "$OUT/contract.txt"

grep -Fqx \
  "MFE_MAE_BASIS=EXECUTION_ENTRY_PRICE" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_FAILURE_ATTRIBUTION_V1_READY" \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE analytics" \
  "DELETE FROM analytics" \
  "ALTER TABLE" \
  "DROP TABLE" \
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
echo "VERDICT=TEST_POSTGRESQL_EDGE_FAILURE_ATTRIBUTION_V1_OK"
