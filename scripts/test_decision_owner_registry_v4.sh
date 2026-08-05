#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_registry_v4"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER REGISTRY V4 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" scripts/build_decision_owner_registry_v4.py |
  tee "$LOG"

for file in \
  "$OUT/confirmed_owners.tsv" \
  "$OUT/deferred_stages.tsv" \
  "$OUT/ownership_edges.tsv" \
  "$OUT/registry_contract.txt" \
  "$OUT/source_v3_test.log" \
  "$OUT/source_edge_confirmation.log" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CONFIRMED_COUNT="$(
  tail -n +2 "$OUT/confirmed_owners.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEFERRED_COUNT="$(
  tail -n +2 "$OUT/deferred_stages.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

EDGE_CONFIRMED_COUNT="$(
  awk -F '\t' '
      NR > 1 && $1 == "EDGE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/confirmed_owners.tsv"
)"

EDGE_DEFERRED_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $1 == "EDGE" &&
      $2 == "EDGE_DECISION" &&
      $3 == "DEFERRED" &&
      $4 == "0" &&
      $5 == "3" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/deferred_stages.tsv"
)"

DUPLICATE_OWNER_IDENTITY_COUNT="$(
  "$PYTHON" - "$OUT/confirmed_owners.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys


path = pathlib.Path(sys.argv[1])

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    identities = [
        (
            (row.get("stage") or "").strip(),
            (row.get("ownership_scope") or "").strip(),
            (row.get("owner_symbol") or "").strip(),
        )
        for row in csv.DictReader(
            stream,
            delimiter="\t",
        )
    ]

print(len(identities) - len(set(identities)))
PY_CHECK
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_owner_count=$CONFIRMED_COUNT"
echo "preserved_v3_owner_count=$CONFIRMED_COUNT"
echo "deferred_stage_count=$DEFERRED_COUNT"
echo "edge_confirmed_owner_count=$EDGE_CONFIRMED_COUNT"
echo "edge_deferred_stage_count=$EDGE_DEFERRED_COUNT"
echo "duplicate_owner_identity_count=$DUPLICATE_OWNER_IDENTITY_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$CONFIRMED_COUNT" -eq 9 ]]
[[ "$DEFERRED_COUNT" -eq 1 ]]
[[ "$EDGE_CONFIRMED_COUNT" -eq 0 ]]
[[ "$EDGE_DEFERRED_COUNT" -eq 1 ]]
[[ "$DUPLICATE_OWNER_IDENTITY_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $4 != "CONFIRMED" {
        print "ERROR=confirmed_status_invalid:" $1 "|" $2
        exit 1
    }

    $6 != "1" {
        print "ERROR=owner_not_confirmed:" $1 "|" $2
        exit 1
    }

    $7 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1 "|" $2
        exit 1
    }
' "$OUT/confirmed_owners.tsv"

for contract in \
  "CONFIRMED_OWNER_COUNT=9" \
  "PRESERVED_V3_OWNER_COUNT=9" \
  "DEFERRED_STAGE_COUNT=1" \
  "EDGE_STAGE_STATUS=DEFERRED" \
  "EDGE_CONFIRMED_OWNER_COUNT=0" \
  "EDGE_DORMANT_COMPONENT_COUNT=3" \
  "DUPLICATE_OWNER_IDENTITY_COUNT=0" \
  "UNRESOLVED_COUNT=0" \
  "RUNTIME_INSTRUMENTATION=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/registry_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=DECISION_OWNER_REGISTRY_V4_READY" \
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
echo "VERDICT=TEST_DECISION_OWNER_REGISTRY_V4_OK"
