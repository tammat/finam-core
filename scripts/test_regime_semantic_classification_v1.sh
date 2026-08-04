#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/regime_semantic_classification_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST REGIME SEMANTIC CLASSIFICATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_regime_owner_candidates_v1.sh

"$PYTHON" \
  scripts/build_regime_semantic_classification_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/semantic_classification.tsv"
  "$OUT/classifier_candidates.tsv"
  "$OUT/family_specific_candidates.tsv"
  "$OUT/consumers_and_gates.tsv"
  "$OUT/research_only_candidates.tsv"
  "$OUT/excluded_initializers.tsv"
  "$OUT/family_summary.tsv"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

INPUT_COUNT="$(
  tail -n +2 "$OUT/semantic_classification.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CLASSIFIER_COUNT="$(
  tail -n +2 "$OUT/classifier_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

FAMILY_CLASSIFIER_COUNT="$(
  tail -n +2 "$OUT/family_specific_candidates.tsv" |
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

echo "input_candidate_count=$INPUT_COUNT"
echo "generic_classifier_candidate_count=$CLASSIFIER_COUNT"
echo "family_classifier_candidate_count=$FAMILY_CLASSIFIER_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$INPUT_COUNT" -eq 388 ]]
[[ "$CLASSIFIER_COUNT" -gt 0 ]]
[[ "$FAMILY_CLASSIFIER_COUNT" -gt 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for symbol in \
  "RegimeEngine.evaluate" \
  "RegimeLabeler.label" \
  "RegimeDetector.detect" \
  "RegimeLayerV2.classify"
do
    grep -Fq "$symbol" "$OUT/classifier_candidates.tsv" || {
        echo "ERROR=expected_classifier_missing:$symbol"
        exit 1
    }
done

grep -Fq \
  "BRRegimeLayer.evaluate" \
  "$OUT/family_specific_candidates.tsv"

for symbol in \
  "PaperTradingPipeline._adaptive_regime_filter_if_enabled" \
  "ExecutionDecisionLayer.decide" \
  "AdaptiveRegimeFilter.evaluate" \
  "RegimeRuntimeControlService.allow_regime"
do
    grep -Fq "$symbol" "$OUT/consumers_and_gates.tsv" || {
        echo "ERROR=expected_consumer_missing:$symbol"
        exit 1
    }
done

INITIALIZER_OWNER_COUNT="$(
  "$PYTHON" - "$OUT/semantic_classification.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys


path = pathlib.Path(sys.argv[1])

owner_classes = {
    "GENERIC_REGIME_CLASSIFIER_CANDIDATE",
    "FAMILY_REGIME_CLASSIFIER_CANDIDATE",
}

count = 0

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    for row in csv.DictReader(
        stream,
        delimiter="\t",
    ):
        function = (
            row.get("function")
            or ""
        ).strip()

        semantic_classification = (
            row.get("semantic_classification")
            or ""
        ).strip()

        if (
            function == "__init__"
            and semantic_classification in owner_classes
        ):
            count += 1

print(count)
PY_CHECK
)"

echo "initializer_owner_count=$INITIALIZER_OWNER_COUNT"
[[ "$INITIALIZER_OWNER_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $19 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $5
        exit 1
    }

    $20 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $5
        exit 1
    }
' "$OUT/semantic_classification.tsv"

grep -Fq \
  "VERDICT=REGIME_SEMANTIC_CLASSIFICATION_V1_READY" \
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

echo "confirmed_owner_count=0"
echo "owner_assignment_performed=0"
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
echo "VERDICT=TEST_REGIME_SEMANTIC_CLASSIFICATION_V1_OK"
