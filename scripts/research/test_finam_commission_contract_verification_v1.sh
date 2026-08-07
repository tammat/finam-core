#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_finam_commission_contract_verification_v1.py"

BATCH_ID="${1:-PG_EDGE_FAMILY_EXPANSION_V1_20260806_073217}"
OUT="/tmp/finam_commission_contract_verification_v1/$BATCH_ID"
LOG="/tmp/test_finam_commission_contract_verification_v1.log"

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
  "$OUT/commission_contract.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=missing_output:$file"
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

PERSISTENCE_OK_COUNT="$(
  awk -F= '
      $1 == "PERSISTENCE_OK_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

WITHIN_BREAK_EVEN_COUNT="$(
  awk -F= '
      $1 == "COMMISSION_WITHIN_BREAK_EVEN_COUNT" {
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
echo "persistence_ok_count=$PERSISTENCE_OK_COUNT"
echo "commission_within_break_even_count=$WITHIN_BREAK_EVEN_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$RUN_COUNT" -eq 16 ]]
[[ "$PERSISTENCE_OK_COUNT" -eq 16 ]]
[[ "$WITHIN_BREAK_EVEN_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx \
  "EXTERNAL_TARIFF_VERIFIED=0" \
  "$OUT/contract.txt"

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

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FINAM_COMMISSION_CONTRACT_VERIFICATION_V1_OK"
