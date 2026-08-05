#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_semantic_classification_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EDGE SEMANTIC CLASSIFICATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_edge_owner_candidates_v1.sh

"$PYTHON" \
  scripts/build_edge_semantic_classification_v1.py \
  | tee "$LOG"

for file in \
  "$OUT/semantic_classification.tsv" \
  "$OUT/authoritative_decision_candidates.tsv" \
  "$OUT/validation_engines.tsv" \
  "$OUT/metric_calculators.tsv" \
  "$OUT/promotion_and_ranking.tsv" \
  "$OUT/runtime_guards.tsv" \
  "$OUT/research_only.tsv" \
  "$OUT/excluded_candidates.tsv" \
  "$OUT/summary.tsv" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

INPUT_COUNT="$(
  tail -n +2 \
    "$OUT/semantic_classification.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

AUTHORITATIVE_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $9 == "AUTHORITATIVE_EDGE_DECISION_CANDIDATE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/authoritative_decision_candidates.tsv"
)"

VALIDATION_COUNT="$(
  tail -n +2 \
    "$OUT/validation_engines.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

METRIC_COUNT="$(
  tail -n +2 \
    "$OUT/metric_calculators.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 \
    "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "input_candidate_count=$INPUT_COUNT"
echo "authoritative_candidate_count=$AUTHORITATIVE_COUNT"
echo "validation_engine_count=$VALIDATION_COUNT"
echo "metric_calculator_count=$METRIC_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$INPUT_COUNT" -eq 444 ]]
[[ "$AUTHORITATIVE_COUNT" -eq 3 ]]
[[ "$VALIDATION_COUNT" -gt 0 ]]
[[ "$METRIC_COUNT" -gt 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

"$PYTHON" - "$OUT/authoritative_decision_candidates.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys


path = pathlib.Path(sys.argv[1])

expected = {
    (
        "src/finam_core/analytics/directional_edge_guard.py",
        "DirectionalEdgeGuard.decide",
    ),
    (
        "src/finam_core/analytics/statistical_validation_decision.py",
        "StatisticalValidationDecisionEngine.decide",
    ),
    (
        "src/finam_core/analytics/session_edge_guard.py",
        "SessionEdgeGuard.decide",
    ),
}

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    rows = list(
        csv.DictReader(
            stream,
            delimiter="\t",
        )
    )

actual = {
    (
        (row.get("path") or "").strip(),
        (row.get("qualified_name") or "").strip(),
    )
    for row in rows
    if (
        row.get("semantic_classification")
        == "AUTHORITATIVE_EDGE_DECISION_CANDIDATE"
    )
}

missing = sorted(expected - actual)
unexpected = sorted(actual - expected)

if missing:
    raise SystemExit(
        "ERROR=authoritative_identity_missing:"
        + ",".join(
            f"{item[0]}|{item[1]}"
            for item in missing
        )
    )

if unexpected:
    raise SystemExit(
        "ERROR=unexpected_authoritative_identity:"
        + ",".join(
            f"{item[0]}|{item[1]}"
            for item in unexpected
        )
    )

print(f"authoritative_identity_count={len(actual)}")
print("authoritative_identity_contract=OK")
PY_CHECK

grep -Fq \
  $'RISK\tsrc/finam_core/risk/session_edge_guard.py\tSessionEdgeGuard\tdecide\tSessionEdgeGuard.decide' \
  "$OUT/semantic_classification.tsv"

grep -Fq \
  "EDGE_RISK_CONSUMER" \
  "$OUT/semantic_classification.tsv"

for symbol in \
  "EdgeValidationEngine.validate" \
  "StatisticalValidationEngine.validate" \
  "evaluate_walk_forward"
do
    grep -Fq \
      "$symbol" \
      "$OUT/validation_engines.tsv" || {
          echo "ERROR=validation_engine_missing:$symbol"
          exit 1
      }
done

for symbol in \
  "StrategyScorecardCalculator.calculate" \
  "calculate_trade_statistics"
do
    grep -Fq \
      "$symbol" \
      "$OUT/metric_calculators.tsv" || {
          echo "ERROR=metric_calculator_missing:$symbol"
          exit 1
      }
done

awk -F '\t' '
    NR == 1 {
        next
    }

    $11 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $5
        exit 1
    }

    $12 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $5
        exit 1
    }
' "$OUT/semantic_classification.tsv"

grep -Fq \
  "VERDICT=EDGE_SEMANTIC_CLASSIFICATION_V1_READY" \
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
echo "VERDICT=TEST_EDGE_SEMANTIC_CLASSIFICATION_V1_OK"
