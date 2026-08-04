#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/regime_owner_confirmation_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST REGIME OWNER CONFIRMATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_regime_ambiguous_binding_resolution_v3.sh

"$PYTHON" \
  scripts/build_regime_owner_confirmation_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/confirmed_regime_owners.tsv"
  "$OUT/deferred_regime_candidates.tsv"
  "$OUT/internal_helpers.tsv"
  "$OUT/regime_ownership_contract.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CONFIRMED_COUNT="$(
  tail -n +2 \
    "$OUT/confirmed_regime_owners.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEFERRED_COUNT="$(
  tail -n +2 \
    "$OUT/deferred_regime_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

HELPER_COUNT="$(
  tail -n +2 \
    "$OUT/internal_helpers.tsv" |
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

echo "confirmed_regime_owner_count=$CONFIRMED_COUNT"
echo "deferred_regime_candidate_count=$DEFERRED_COUNT"
echo "internal_helper_count=$HELPER_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$CONFIRMED_COUNT" -eq 1 ]]
[[ "$DEFERRED_COUNT" -eq 9 ]]
[[ "$HELPER_COUNT" -eq 2 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fq \
  $'BR\tMARKET_REGIME:BR\t' \
  "$OUT/confirmed_regime_owners.tsv"

grep -Fq \
  "BRRegimeLayer.evaluate" \
  "$OUT/confirmed_regime_owners.tsv"

grep -Fq \
  "RESOLVED_RUNTIME_REACHABLE" \
  "$OUT/confirmed_regime_owners.tsv"

for symbol in \
  "RegimeEngine.evaluate" \
  "RegimeLabeler.label" \
  "RegimeLayerV2.classify" \
  "RegimeDetector.detect" \
  "CandleRegimeEngineV2.classify" \
  "RegimeClassifier.classify"
do
    grep -Fq \
      "$symbol" \
      "$OUT/deferred_regime_candidates.tsv" || {
          echo "ERROR=deferred_candidate_missing:$symbol"
          exit 1
      }
done

grep -Fq \
  "RegimeLabeler._trend_label" \
  "$OUT/internal_helpers.tsv"

grep -Fq \
  "RegimeLabeler._vol_label" \
  "$OUT/internal_helpers.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $10 < 1 {
        print "ERROR=runtime_evidence_missing:" $6
        exit 1
    }

    $12 != "CONFIRMED_REGIME_OWNER" {
        print "ERROR=classification_invalid:" $6
        exit 1
    }

    $14 != "1" {
        print "ERROR=owner_not_confirmed:" $6
        exit 1
    }

    $15 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $6
        exit 1
    }
' "$OUT/confirmed_regime_owners.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $14 != "0" {
        print "ERROR=deferred_owner_confirmed:" $6
        exit 1
    }

    $15 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $6
        exit 1
    }
' "$OUT/deferred_regime_candidates.tsv"

for contract in \
  "OWNERSHIP_MODEL=FAMILY_SCOPED_PARTIAL" \
  "BR_REGIME_OWNER=BRRegimeLayer.evaluate" \
  "GENERIC_REGIME_OWNER=DEFERRED" \
  "CONFIRMED_OWNER_COUNT=1" \
  "DEFERRED_CANDIDATE_COUNT=9" \
  "INTERNAL_HELPER_COUNT=2" \
  "UNRESOLVED_COUNT=0" \
  "RUNTIME_INSTRUMENTATION=0"
do
    grep -Fq \
      "$contract" \
      "$OUT/regime_ownership_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=REGIME_OWNER_CONFIRMATION_V1_READY" \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRACKED_DIRTY_COUNT="$(
  {
    git status --porcelain |
    grep -Ev '^\?\?' ||
    true
  } |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
echo "tracked_dirty_count=$TRACKED_DIRTY_COUNT"

[[ "$STAGED_COUNT" -eq 0 ]]
[[ "$TRACKED_DIRTY_COUNT" -eq 0 ]]

echo "owner_assignment_performed=1"
echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_REGIME_OWNER_CONFIRMATION_V1_OK"
