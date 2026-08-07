#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_execution_edge_run_ranking_v1.py"

BATCH_ID="${1:-PG_EDGE_FAMILY_EXPANSION_V1_20260806_073217}"
OUT="/tmp/postgresql_execution_edge_run_ranking_v1/$BATCH_ID"
LOG="/tmp/test_postgresql_execution_edge_run_ranking_v1.log"

cd "$ROOT"

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --batch-id "$BATCH_ID" |
tee "$LOG"

for file in \
  "$OUT/run_ranking.tsv" \
  "$OUT/execution_survivors.tsv" \
  "$OUT/commission_break_even.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

RUN_COUNT="$(
  awk -F= '
      $1 == "RUN_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

POSITIVE_EXECUTION_COUNT="$(
  awk -F= '
      $1 == "POSITIVE_EXECUTION_RUN_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

POSITIVE_NET_COUNT="$(
  awk -F= '
      $1 == "POSITIVE_NET_RUN_COUNT" {
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

echo "run_count=$RUN_COUNT"
echo "positive_execution_run_count=$POSITIVE_EXECUTION_COUNT"
echo "positive_net_run_count=$POSITIVE_NET_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$RUN_COUNT" -eq 16 ]]
[[ "$POSITIVE_EXECUTION_COUNT" -gt 0 ]]
[[ "$POSITIVE_NET_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

SURVIVOR_COUNT="$(
  tail -n +2 "$OUT/execution_survivors.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

[[ "$SURVIVOR_COUNT" -eq "$POSITIVE_EXECUTION_COUNT" ]]

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

grep -Fq \
  "VERDICT=POSTGRESQL_EXECUTION_EDGE_RUN_RANKING_V1_READY" \
  "$LOG"

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EXECUTION_EDGE_RUN_RANKING_V1_OK"
