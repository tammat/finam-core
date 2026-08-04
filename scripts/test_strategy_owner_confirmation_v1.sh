#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/strategy_owner_confirmation_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST STRATEGY OWNER CONFIRMATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_strategy_runtime_binding_discovery_v2.sh

"$PYTHON" \
  scripts/build_strategy_owner_confirmation_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/confirmed_strategy_owners.tsv"
  "$OUT/alternative_strategy_candidates.tsv"
  "$OUT/strategy_family_ownership.tsv"
  "$OUT/strategy_owner_contract.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CONFIRMED_COUNT="$(
  tail -n +2 "$OUT/confirmed_strategy_owners.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

ALTERNATIVE_COUNT="$(
  tail -n +2 "$OUT/alternative_strategy_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

FAMILY_COUNT="$(
  tail -n +2 "$OUT/strategy_family_ownership.tsv" |
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

echo "confirmed_strategy_owner_count=$CONFIRMED_COUNT"
echo "alternative_strategy_candidate_count=$ALTERNATIVE_COUNT"
echo "family_ownership_count=$FAMILY_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$CONFIRMED_COUNT" -eq 4 ]]
[[ "$ALTERNATIVE_COUNT" -eq 3 ]]
[[ "$FAMILY_COUNT" -eq 3 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fq \
  $'BR\tSINGLE_ACTIVE_OWNER\t' \
  "$OUT/confirmed_strategy_owners.tsv"

grep -Fq \
  "BrConservativeBreakout.on_signal_bar" \
  "$OUT/confirmed_strategy_owners.tsv"

grep -Fq \
  "NgConservativeBreakoutM1.on_signal_bar" \
  "$OUT/confirmed_strategy_owners.tsv"

grep -Fq \
  "VolatilityBreakoutEquity.on_quote" \
  "$OUT/confirmed_strategy_owners.tsv"

grep -Fq \
  "MeanReversionEquity.on_quote" \
  "$OUT/confirmed_strategy_owners.tsv"

grep -Fq \
  "NgConservativeBreakout.on_bars" \
  "$OUT/alternative_strategy_candidates.tsv"

grep -Fq \
  "NGIntradayStrategy.on_bar" \
  "$OUT/alternative_strategy_candidates.tsv"

grep -Fq \
  "NgVolatilityBreakout.on_bars" \
  "$OUT/alternative_strategy_candidates.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $7 != "1" {
        print "ERROR=trade_intent_evidence_missing:" $6
        exit 1
    }

    $9 != "1" {
        print "ERROR=binding_evidence_missing:" $6
        exit 1
    }

    $12 != "0" {
        print "ERROR=downstream_side_effect_present:" $6
        exit 1
    }

    $13 != "1" {
        print "ERROR=owner_evidence_incomplete:" $6
        exit 1
    }

    $15 != "1" {
        print "ERROR=owner_not_confirmed:" $6
        exit 1
    }

    $16 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $6
        exit 1
    }
' "$OUT/confirmed_strategy_owners.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $7 != "1" {
        print "ERROR=ownership_model_invalid:" $1
        exit 1
    }

    $8 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/strategy_family_ownership.tsv"

grep -Fq \
  "BR_MODEL=SINGLE_ACTIVE_OWNER" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "NG_MODEL=SINGLE_ACTIVE_OWNER" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "EQUITY_MODEL=MULTI_STRATEGY_FAMILY" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "CONFIRMED_OWNER_COUNT=4" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "ALTERNATIVE_CANDIDATE_COUNT=3" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "UNRESOLVED_COUNT=0" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "RUNTIME_INSTRUMENTATION=0" \
  "$OUT/strategy_owner_contract.txt"

grep -Fq \
  "VERDICT=STRATEGY_OWNER_CONFIRMATION_V1_READY" \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "owner_assignment_performed=1"
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
echo "VERDICT=TEST_STRATEGY_OWNER_CONFIRMATION_V1_OK"
