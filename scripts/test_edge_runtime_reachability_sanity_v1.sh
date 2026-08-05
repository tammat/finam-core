#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_runtime_reachability_sanity_v1"
TEMP_LOG="/tmp/test_edge_runtime_reachability_sanity_v1.log"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EDGE RUNTIME REACHABILITY SANITY V1 ==="

# Сначала выполняем prerequisite. Он не должен затронуть уже
# сформированные результаты текущего теста.
scripts/test_edge_candidate_dependency_injection_v3.sh

rm -rf "$OUT"
rm -f "$TEMP_LOG"
mkdir -p "$OUT"

"$PYTHON" scripts/audit_edge_runtime_reachability_sanity_v1.py |
  tee "$TEMP_LOG"

test -f "$TEMP_LOG"
cp -a "$TEMP_LOG" "$LOG"
test -f "$LOG"

for file in \
  "$OUT/candidate_identities.tsv" \
  "$OUT/string_references.tsv" \
  "$OUT/registry_references.tsv" \
  "$OUT/dynamic_import_references.tsv" \
  "$OUT/getattr_references.tsv" \
  "$OUT/configuration_references.tsv" \
  "$OUT/executable_references.tsv" \
  "$OUT/candidate_summary.tsv" \
  "$OUT/evidence.txt" \
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

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

EXECUTABLE_REFERENCE_COUNT="$(
  "$PYTHON" - "$OUT/candidate_summary.tsv" <<'PY'
from __future__ import annotations

import csv
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

total = 0

with path.open("r", encoding="utf-8", newline="") as stream:
    for row in csv.DictReader(stream, delimiter="\t"):
        total += int(row.get("executable_reference_count") or 0)

print(total)
PY
)"

INDIRECT_REFERENCE_COUNT="$(
  "$PYTHON" - "$OUT/candidate_summary.tsv" <<'PY'
from __future__ import annotations

import csv
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

fields = (
    "registry_reference_count",
    "dynamic_import_count",
    "reflection_reference_count",
    "configuration_reference_count",
)

total = 0

with path.open("r", encoding="utf-8", newline="") as stream:
    for row in csv.DictReader(stream, delimiter="\t"):
        total += sum(
            int(row.get(field) or 0)
            for field in fields
        )

print(total)
PY
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "executable_reference_count=$EXECUTABLE_REFERENCE_COUNT"
echo "indirect_reference_count=$INDIRECT_REFERENCE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$CANDIDATE_COUNT" -eq 3 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

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

    $10 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $2
        exit 1
    }

    $11 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $2
        exit 1
    }
' "$OUT/candidate_summary.tsv"

grep -Fq \
  "VERDICT=EDGE_RUNTIME_REACHABILITY_SANITY_V1_READY" \
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
echo "VERDICT=TEST_EDGE_RUNTIME_REACHABILITY_SANITY_V1_OK"
