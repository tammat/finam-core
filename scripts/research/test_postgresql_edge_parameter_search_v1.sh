#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_edge_parameter_search_v1.py"
RUNNER="scripts/research/run_postgresql_edge_parameter_search_v1.py"

BATCH_ID="TEST_PG_EDGE_SEARCH_V1"
OUT="/tmp/postgresql_edge_parameter_search_v1/$BATCH_ID"
LOG="/tmp/test_postgresql_edge_parameter_search_v1.log"

cd "$ROOT"

echo "=== TEST POSTGRESQL EDGE PARAMETER SEARCH V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile \
  "$BUILDER" \
  "$RUNNER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --symbols "LKOH@MISX" \
  --timeframes "M5" \
  --commission-per-side "1.5" \
  --slippage-bps "2.0" \
  --bar-limit 20000 \
  --batch-id "$BATCH_ID" \
  --max-tasks 36 \
  --plan-only |
tee "$LOG"

for file in \
  "$OUT/search_plan.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

TASK_COUNT="$(
  tail -n +2 "$OUT/search_plan.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

ATR_COUNT="$(
  awk -F '\t' '
      NR > 1 && $3 == "ATR_IMPULSE_V1" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/search_plan.tsv"
)"

MOMENTUM_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $3 == "MOMENTUM_CONTINUATION_V1" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/search_plan.tsv"
)"

UNIQUE_HASH_COUNT="$(
  awk -F '\t' '
      NR > 1 {
          seen[$6] = 1
      }

      END {
          for (key in seen) {
              count++
          }
          print count + 0
      }
  ' "$OUT/search_plan.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "task_count=$TASK_COUNT"
echo "atr_task_count=$ATR_COUNT"
echo "momentum_task_count=$MOMENTUM_COUNT"
echo "unique_parameter_hash_count=$UNIQUE_HASH_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$TASK_COUNT" -eq 36 ]]
[[ "$ATR_COUNT" -eq 24 ]]
[[ "$MOMENTUM_COUNT" -eq 12 ]]
[[ "$UNIQUE_HASH_COUNT" -eq 36 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx "TASK_COUNT=36" "$OUT/contract.txt"
grep -Fqx "ATR_TASK_COUNT=24" "$OUT/contract.txt"
grep -Fqx "MOMENTUM_TASK_COUNT=12" "$OUT/contract.txt"
grep -Fqx "PLAN_ONLY=1" "$OUT/contract.txt"
grep -Fqx "DATABASE=POSTGRESQL_ONLY" "$OUT/contract.txt"
grep -Fqx "RUNTIME_CHANGED=0" "$OUT/contract.txt"
grep -Fqx "EXECUTION_CHANGED=0" "$OUT/contract.txt"
grep -Fqx "ORDERS_CHANGED=0" "$OUT/contract.txt"
grep -Fqx "FILLS_CHANGED=0" "$OUT/contract.txt"
grep -Fqx "MICRO_LIVE_ALLOWED=0" "$OUT/contract.txt"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_READY" \
  "$LOG"

for marker in \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order(" \
  "execution_enabled = true" \
  "micro_live_allowed = true"
do
    COUNT="$(
      {
        grep -F "$marker" "$BUILDER" "$RUNNER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRACKED_DIRTY_COUNT="$(
  {
    git status --porcelain |
    grep -Ev '^\?\?' ||
    true
  } |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
echo "tracked_dirty_count=$TRACKED_DIRTY_COUNT"

[[ "$STAGED_COUNT" -eq 0 ]]
[[ "$TRACKED_DIRTY_COUNT" -eq 0 ]]

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_OK"
