#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/execution_broker_result_ownership_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EXECUTION BROKER RESULT OWNERSHIP V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_execution_broker_result_ownership_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/execution_methods.tsv"
  "$OUT/broker_methods.tsv"
  "$OUT/result_flow_edges.tsv"
  "$OUT/result_contracts.tsv"
  "$OUT/exception_contracts.tsv"
  "$OUT/ownership_candidates.tsv"
  "$OUT/evidence.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

EXECUTION_METHOD_COUNT="$(
  tail -n +2 "$OUT/execution_methods.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

BROKER_METHOD_COUNT="$(
  tail -n +2 "$OUT/broker_methods.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "execution_method_count=$EXECUTION_METHOD_COUNT"
echo "broker_method_count=$BROKER_METHOD_COUNT"

[[ "$EXECUTION_METHOD_COUNT" -eq 2 ]]
[[ "$BROKER_METHOD_COUNT" -eq 2 ]]

grep -q \
  $'^EXECUTION\t.*execution_dispatcher.py\texecute\t' \
  "$OUT/execution_methods.tsv"

grep -q \
  $'^EXECUTION\t.*execution_dispatcher.py\tplace_limit_order\t' \
  "$OUT/execution_methods.tsv"

grep -q \
  $'^BROKER\t.*orders_client.py\tplace_limit_order\t' \
  "$OUT/broker_methods.tsv"

grep -q \
  $'^BROKER\t.*orders_client.py\tplace_market_order\t' \
  "$OUT/broker_methods.tsv"

grep -q \
  $'^BROKER_ACK_REJECT\tBROKER\t.*orders_client.py\tFinamOrdersClient\t' \
  "$OUT/ownership_candidates.tsv"

awk -F '\t' '
    {
        for (column = 1; column <= NF; column++) {
            sub(/\r$/, "", $column)
        }
    }

    NR == 1 {
        next
    }

    $7 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $1
        exit 1
    }

    $8 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/ownership_candidates.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $12 != "0" || $13 != "0" {
        print "ERROR=execution_owner_or_runtime_enabled:" $3
        exit 1
    }
' "$OUT/execution_methods.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $12 != "0" || $13 != "0" {
        print "ERROR=broker_owner_or_runtime_enabled:" $3
        exit 1
    }
' "$OUT/broker_methods.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=EXECUTION_BROKER_RESULT_OWNERSHIP_V1_READY$' \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "TRUNCATE " \
  "DROP TABLE" \
  "ALTER TABLE" \
  "systemctl restart" \
  "systemctl start" \
  "systemctl stop"
do
    count="$(
      {
        grep -F "$marker" \
          scripts/audit_execution_broker_result_ownership_v1.py \
          2>/dev/null || true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_action_marker=$marker count=$count"
    [[ "$count" -eq 0 ]]
done

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "owner_assignment_performed=0"
echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EXECUTION_BROKER_RESULT_OWNERSHIP_V1_OK"
