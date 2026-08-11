#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_active_challenger_evidence_priority_v2.py"

echo "=== TEST ACTIVE CHALLENGER EVIDENCE PRIORITY V2 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q \
'^EVIDENCE_PRIORITY_ROW rank=1 .*symbol=BR .*candidate=IMMEDIATE_S1.5_R1.6 .*pairs=46 ' \
<<< "$OUTPUT"

grep -q \
'^EVIDENCE_PRIORITY_ROW rank=2 .*symbol=SBERP .*candidate=CONFIRM_1_S1.8_R1.8 .*pairs=16 ' \
<<< "$OUTPUT"

grep -q \
'^EVIDENCE_PRIORITY_ROW rank=3 .*symbol=SBER .*candidate=IMMEDIATE_S1.5_R1.6 .*pairs=1 ' \
<<< "$OUTPUT"

grep -q '^active_challengers=29$' <<< "$OUTPUT"
grep -q '^evidence_priority_candidates=3$' <<< "$OUTPUT"
grep -q '^validation_candidates=0$' <<< "$OUTPUT"
grep -q '^early_positive_signals=3$' <<< "$OUTPUT"

grep -q '^v1_rank_used_for_edge_strength=0$' <<< "$OUTPUT"
grep -q '^sample_maturity_used_for_priority=1$' <<< "$OUTPUT"
grep -q '^positive_net_required=1$' <<< "$OUTPUT"
grep -q '^placebo_pass_required=1$' <<< "$OUTPUT"
grep -q '^positive_delta_lower_bound_required=1$' <<< "$OUTPUT"

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
'^VERDICT=ACTIVE_CHALLENGER_EVIDENCE_PRIORITY_V2_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_ACTIVE_CHALLENGER_EVIDENCE_PRIORITY_V2_OK"
