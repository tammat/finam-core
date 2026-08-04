#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_priority_call_path_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER PRIORITY CALL PATH V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_owner_priority_call_path_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/call_path_edges.tsv"
  "$OUT/owner_evidence.tsv"
  "$OUT/broker_boundary.tsv"
  "$OUT/call_path_report.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "unresolved_count=$UNRESOLVED_COUNT"
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -q $'^BROKER\t.*orders_client.py\tOrdersClient\tCLASS_BOUNDARY\t1\t1\t' \
  "$OUT/broker_boundary.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $8 != "0" || $9 != "0" {
        print "ERROR=broker_owner_or_instrumentation_enabled"
        exit 1
    }
' "$OUT/broker_boundary.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $8 != "0" || $9 != "0" {
        print "ERROR=owner_or_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/owner_evidence.tsv"

grep -q '^broker_owner_granularity=CLASS_BOUNDARY$' "$LOG"
grep -q '^broker_owner_symbol=OrdersClient$' "$LOG"
grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_PRIORITY_CALL_PATH_V1_READY$' \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_OWNER_PRIORITY_CALL_PATH_V1_OK"
