#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_cost_mismatch_diagnostics_v1"
SOURCE="/tmp/edge_cost_recalculation_v1"
LOG="/tmp/test_edge_cost_mismatch_diagnostics_v1.log"

cd "$ROOT"

echo "=== TEST EDGE COST MISMATCH DIAGNOSTICS V1 ==="

if [[ ! -f "$SOURCE/recalculated_edges.tsv" ]]; then
    scripts/research/test_edge_cost_recalculation_v1.sh
fi

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/build_edge_cost_mismatch_diagnostics_v1.py |
tee "$LOG"

for file in \
  "$OUT/mismatch_details.tsv" \
  "$OUT/mismatch_summary.tsv" \
  "$OUT/strategy_summary.tsv" \
  "$OUT/formula_hypotheses.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

MISMATCH_COUNT="$(
  tail -n +2 "$OUT/mismatch_details.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

SUMMARY_TOTAL="$(
  awk -F '\t' '
      NR > 1 {
          total += $2
      }

      END {
          print total + 0
      }
  ' "$OUT/mismatch_summary.tsv"
)"

LKOH_ATR_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $1 == "ATR_IMPULSE_V1" &&
      $2 == "LKOH@MISX" &&
      $3 == "M1" {
          count += $4
      }

      END {
          print count + 0
      }
  ' "$OUT/strategy_summary.tsv"
)"

echo "mismatch_count=$MISMATCH_COUNT"
echo "summary_failure_total=$SUMMARY_TOTAL"
echo "lkoh_atr_impulse_mismatch_count=$LKOH_ATR_COUNT"

[[ "$MISMATCH_COUNT" -eq 476 ]]
[[ "$SUMMARY_TOTAL" -ge "$MISMATCH_COUNT" ]]
[[ "$LKOH_ATR_COUNT" -gt 0 ]]

grep -Fqx \
  "MODE=READ_ONLY_ARTIFACT_ANALYSIS" \
  "$OUT/contract.txt"

grep -Fqx \
  "MISMATCH_ROW_COUNT=476" \
  "$OUT/contract.txt"

grep -Fqx \
  "HYPOTHESES_CONFIRMED=0" \
  "$OUT/contract.txt"

grep -Fqx \
  "DB_WRITES_PERFORMED=0" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=EDGE_COST_MISMATCH_DIAGNOSTICS_V1_READY" \
  "$LOG"

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_COST_MISMATCH_DIAGNOSTICS_V1_OK"
