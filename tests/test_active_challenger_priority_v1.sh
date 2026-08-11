#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_active_challenger_priority_v1.py"

echo "=== TEST ACTIVE CHALLENGER PRIORITY V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q '^active_challengers=28$' <<< "$OUTPUT"
grep -q '^positive_net_candidates=2$' <<< "$OUTPUT"
grep -q '^positive_and_placebo_pass=2$' <<< "$OUTPUT"

grep -q \
  '^oos_pair_evidence_not_equated_to_admission=1$' \
  <<< "$OUTPUT"

grep -q '^thresholds_changed=0$' <<< "$OUTPUT"
grep -q '^net_first_logic_changed=0$' <<< "$OUTPUT"
grep -q '^placebo_logic_changed=0$' <<< "$OUTPUT"
grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
  '^VERDICT=ACTIVE_CHALLENGER_PRIORITY_V1_READY$' \
  <<< "$OUTPUT"

echo "VERDICT=TEST_ACTIVE_CHALLENGER_PRIORITY_V1_OK"
