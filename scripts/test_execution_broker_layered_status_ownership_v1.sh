#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/execution_broker_layered_status_ownership_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EXECUTION BROKER LAYERED STATUS OWNERSHIP V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/build_execution_broker_layered_status_ownership_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/confirmed_status_owners.tsv"
  "$OUT/ownership_edges.tsv"
  "$OUT/ownership_contract.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

OWNER_COUNT="$(
  tail -n +2 "$OUT/confirmed_status_owners.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_result_owner_count=$OWNER_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$OWNER_COUNT" -eq 2 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -q \
  $'^BROKER\tBROKER_PROTOCOL_RESULT\tFinamOrdersClient\tCLASS_BOUNDARY\tCONFIRMED_RESULT_OWNER\t' \
  "$OUT/confirmed_status_owners.tsv"

grep -q \
  $'^EXECUTION\tEXECUTION_DOMAIN_STATUS\tExecutionDispatcher\tCLASS_BOUNDARY\tCONFIRMED_RESULT_OWNER\t' \
  "$OUT/confirmed_status_owners.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $7 != "1" || $8 != "1" {
        print "ERROR=incomplete_mapping_evidence:" $1
        exit 1
    }

    $9 != "1" {
        print "ERROR=owner_not_confirmed:" $1
        exit 1
    }

    $10 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/confirmed_status_owners.tsv"

grep -q \
  $'^BROKER_PROTOCOL_RESULT_TO_EXECUTION_DOMAIN_STATUS\tBROKER\tFinamOrdersClient\tEXECUTION\tExecutionDispatcher\tLAYERED_STATUS_TRANSFORMATION\t1\t0$' \
  "$OUT/ownership_edges.tsv"

grep -q '^DUPLICATE_OWNERSHIP=0$' \
  "$OUT/ownership_contract.txt"

grep -q '^RUNTIME_INSTRUMENTATION=0$' \
  "$OUT/ownership_contract.txt"

grep -q '^duplicate_ownership_scope_count=0$' "$LOG"
grep -q '^broker_protocol_owner_confirmed=1$' "$LOG"
grep -q '^execution_domain_owner_confirmed=1$' "$LOG"
grep -q '^ownership_edge_reachable=1$' "$LOG"
grep -q \
  '^VERDICT=EXECUTION_BROKER_LAYERED_STATUS_OWNERSHIP_V1_READY$' \
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
echo "VERDICT=TEST_EXECUTION_BROKER_LAYERED_STATUS_OWNERSHIP_V1_OK"
