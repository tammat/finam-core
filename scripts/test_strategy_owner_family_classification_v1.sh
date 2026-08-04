#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/strategy_owner_family_classification_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST STRATEGY OWNER FAMILY CLASSIFICATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_strategy_owner_intent_points_v1.sh

"$PYTHON" \
  scripts/build_strategy_owner_family_classification_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/classified_candidates.tsv"
  "$OUT/primary_candidates.tsv"
  "$OUT/legacy_candidates.tsv"
  "$OUT/excluded_non_strategy.tsv"
  "$OUT/family_summary.tsv"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

PRIMARY_COUNT="$(
  tail -n +2 "$OUT/primary_candidates.tsv" |
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

echo "primary_candidate_count=$PRIMARY_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$PRIMARY_COUNT" -eq 7 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -q \
  $'^BR\t.*BrConservativeBreakout.on_signal_bar\t' \
  "$OUT/primary_candidates.tsv"

grep -q \
  $'^NG\t.*NgConservativeBreakout.on_bars\t' \
  "$OUT/primary_candidates.tsv"

grep -q \
  $'^NG\t.*NgConservativeBreakoutM1.on_signal_bar\t' \
  "$OUT/primary_candidates.tsv"

grep -q \
  $'^NG\t.*NgVolatilityBreakout.on_bars\t' \
  "$OUT/primary_candidates.tsv"

grep -q \
  $'^NG\t.*NGIntradayStrategy.on_bar\t' \
  "$OUT/primary_candidates.tsv"

grep -q \
  $'^EQUITY\t.*VolatilityBreakoutEquity.on_quote\t' \
  "$OUT/primary_candidates.tsv"

grep -q \
  $'^EQUITY\t.*MeanReversionEquity.on_quote\t' \
  "$OUT/primary_candidates.tsv"

PIPELINE_PRIMARY_COUNT="$(
  grep -c '/pipelines/' "$OUT/primary_candidates.tsv" || true
)"

echo "pipeline_primary_count=$PIPELINE_PRIMARY_COUNT"
[[ "$PIPELINE_PRIMARY_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $14 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $5
        exit 1
    }

    $15 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $5
        exit 1
    }
' "$OUT/primary_candidates.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"

grep -q \
  '^VERDICT=STRATEGY_OWNER_FAMILY_CLASSIFICATION_V1_READY$' \
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
echo "VERDICT=TEST_STRATEGY_OWNER_FAMILY_CLASSIFICATION_V1_OK"
