#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_finam_actual_commission_evidence_v1.py"

FIXTURE="/tmp/finam_actual_commission_evidence_v1_fixture.tsv"
OUT="/tmp/finam_actual_commission_evidence_v1_test"
LOG="/tmp/test_finam_actual_commission_evidence_v1.log"

cd "$ROOT"

rm -rf "$OUT"
rm -f "$FIXTURE" "$LOG"

cat > "$FIXTURE" <<'TSV'
evidence_id	account_tariff	trade_date	symbol	market	quantity_lots	lot_size	entry_turnover	exit_turnover	broker_commission_entry	broker_commission_exit	exchange_fee_entry	exchange_fee_exit	other_fee_entry	other_fee_exit	source_document	source_row_reference
TEST_SBER_001	TEST_TARIFF	2026-08-01	SBER@MISX	MOEX	1	10	3200.00	3210.00	0.10	0.10	0.02	0.02	0	0	TEST_ONLY	ROW_1
TEST_SBER_002	TEST_TARIFF	2026-08-02	SBER@MISX	MOEX	1	10	3210.00	3220.00	0.11	0.11	0.02	0.02	0	0	TEST_ONLY	ROW_2
TSV

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --input "$FIXTURE" \
  --output "$OUT" |
tee "$LOG"

for file in \
  "$OUT/normalized_evidence.tsv" \
  "$OUT/instrument_summary.tsv" \
  "$OUT/break_even_comparison.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

EVIDENCE_COUNT="$(
  awk -F= '
    $1 == "EVIDENCE_ROW_COUNT" {print $2}
  ' "$OUT/contract.txt"
)"

TARGET_GROUP_COUNT="$(
  awk -F= '
    $1 == "TARGET_EVIDENCE_GROUP_COUNT" {print $2}
  ' "$OUT/contract.txt"
)"

WITHIN_BREAK_EVEN_COUNT="$(
  awk -F= '
    $1 == "TARGET_WITHIN_BREAK_EVEN_COUNT" {print $2}
  ' "$OUT/contract.txt"
)"

UNRESOLVED_COUNT="$(
  awk -F= '
    $1 == "UNRESOLVED_COUNT" {print $2}
  ' "$OUT/contract.txt"
)"

echo "evidence_row_count=$EVIDENCE_COUNT"
echo "target_group_count=$TARGET_GROUP_COUNT"
echo "within_break_even_count=$WITHIN_BREAK_EVEN_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$EVIDENCE_COUNT" -eq 2 ]]
[[ "$TARGET_GROUP_COUNT" -eq 1 ]]
[[ "$WITHIN_BREAK_EVEN_COUNT" -eq 1 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fq \
  "VERDICT=FINAM_ACTUAL_COMMISSION_EVIDENCE_V1_READY" \
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

echo "fixture_is_actual_evidence=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FINAM_ACTUAL_COMMISSION_EVIDENCE_V1_OK"
