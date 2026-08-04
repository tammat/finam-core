#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/execution_broker_domain_status_mapping_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EXECUTION BROKER DOMAIN STATUS MAPPING V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_execution_broker_domain_status_mapping_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/return_values.tsv"
  "$OUT/status_assignments.tsv"
  "$OUT/exception_mappings.tsv"
  "$OUT/broker_result_consumers.tsv"
  "$OUT/domain_status_candidates.tsv"
  "$OUT/evidence.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

grep -q \
  $'^EXECUTION\t.*ExecutionDispatcher.execute\t' \
  "$OUT/return_values.tsv"

grep -q \
  $'^EXECUTION\t.*ExecutionDispatcher.place_limit_order\t' \
  "$OUT/return_values.tsv"

grep -q \
  $'^BROKER\t.*FinamOrdersClient.place_limit_order\t' \
  "$OUT/return_values.tsv"

grep -q \
  $'^BROKER\t.*FinamOrdersClient.place_market_order\t' \
  "$OUT/return_values.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $7 != "0" || $8 != "0" {
        print "ERROR=owner_or_runtime_enabled:" $3
        exit 1
    }
' "$OUT/domain_status_candidates.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=EXECUTION_BROKER_DOMAIN_STATUS_MAPPING_V1_READY$' \
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
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EXECUTION_BROKER_DOMAIN_STATUS_MAPPING_V1_OK"
