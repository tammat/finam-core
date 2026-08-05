#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_candidate_dependency_injection_v3"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EDGE CANDIDATE DEPENDENCY INJECTION V3 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_edge_semantic_classification_v1.sh

"$PYTHON" scripts/audit_edge_candidate_dependency_injection_v3.py |
  tee "$LOG"

for file in \
  "$OUT/candidate_identities.tsv" \
  "$OUT/import_sites.tsv" \
  "$OUT/annotation_bindings.tsv" \
  "$OUT/parameter_bindings.tsv" \
  "$OUT/factory_returns.tsv" \
  "$OUT/module_instances.tsv" \
  "$OUT/dependency_assignments.tsv" \
  "$OUT/resolved_decide_calls.tsv" \
  "$OUT/candidate_summary.tsv" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CANDIDATE_COUNT="$(
  tail -n +2 "$OUT/candidate_summary.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

RESOLVED_CALL_COUNT="$(
  tail -n +2 "$OUT/resolved_decide_calls.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CANDIDATE_WITH_EVIDENCE_COUNT="$(
  "$PYTHON" - "$OUT/candidate_summary.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys


path = pathlib.Path(sys.argv[1])

evidence_fields = (
    "import_count",
    "parameter_binding_count",
    "annotation_binding_count",
    "factory_return_count",
    "module_instance_count",
    "dependency_assignment_count",
    "resolved_call_count",
)

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
        if any(
            int(row.get(field) or 0) > 0
            for field in evidence_fields
        ):
            count += 1

print(count)
PY_CHECK
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "resolved_call_count=$RESOLVED_CALL_COUNT"
echo "candidate_with_dependency_evidence_count=$CANDIDATE_WITH_EVIDENCE_COUNT"

[[ "$CANDIDATE_COUNT" -eq 3 ]]

for symbol in \
  "DirectionalEdgeGuard.decide" \
  "StatisticalValidationDecisionEngine.decide" \
  "SessionEdgeGuard.decide"
do
    grep -Fq "$symbol" "$OUT/candidate_summary.tsv" || {
        echo "ERROR=candidate_missing:$symbol"
        exit 1
    }
done

awk -F '\t' '
    NR == 1 {
        next
    }

    $11 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $2
        exit 1
    }

    $12 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $2
        exit 1
    }
' "$OUT/candidate_summary.tsv"

grep -Fq \
  "VERDICT=EDGE_CANDIDATE_DEPENDENCY_INJECTION_V3_READY" \
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
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_CANDIDATE_DEPENDENCY_INJECTION_V3_OK"
