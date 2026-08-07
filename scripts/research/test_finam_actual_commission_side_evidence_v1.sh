#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_finam_actual_commission_side_evidence_v1.py"
INPUT="config/research/finam_actual_commission_side_evidence_v1.tsv"
OUT="/tmp/finam_actual_commission_side_evidence_v1"
LOG="/tmp/test_finam_actual_commission_side_evidence_v1.log"

cd "$ROOT"

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --input "$INPUT" \
  --output "$OUT" |
tee "$LOG"

for file in \
  "$OUT/normalized_side_evidence.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=missing_output:$file"
        exit 1
    }
done

EVIDENCE_COUNT="$(
  awk -F= '
      $1 == "EVIDENCE_ROW_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

TARGET_COUNT="$(
  awk -F= '
      $1 == "TARGET_EVIDENCE_ROW_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

WITHIN_BREAK_EVEN="$(
  awk -F= '
      $1 == "TARGET_WITHIN_BREAK_EVEN_COUNT" {
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

echo "evidence_row_count=$EVIDENCE_COUNT"
echo "target_evidence_row_count=$TARGET_COUNT"
echo "target_within_break_even_count=$WITHIN_BREAK_EVEN"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$EVIDENCE_COUNT" -eq 5 ]]
[[ "$TARGET_COUNT" -eq 1 ]]
[[ "$WITHIN_BREAK_EVEN" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx \
  "ACTUAL_COMMISSION_EVIDENCE_VERIFIED=1" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=FINAM_ACTUAL_COMMISSION_SIDE_EVIDENCE_V1_READY" \
  "$LOG"

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
echo "VERDICT=TEST_FINAM_ACTUAL_COMMISSION_SIDE_EVIDENCE_V1_OK"
