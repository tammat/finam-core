#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_active_challenger_evidence_priority_v3.py"

echo "=== TEST ACTIVE CHALLENGER EVIDENCE PRIORITY V3 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q \
'state=POSITIVE_ABSOLUTE_BUT_BASELINE_INFERIOR .*symbol=BR .*pairs=46 ' \
<<< "$OUTPUT"

grep -q \
'state=POSITIVE_ABSOLUTE_BUT_BASELINE_INFERIOR .*symbol=SBERP .*pairs=16 ' \
<<< "$OUTPUT"

grep -q \
'state=INSUFFICIENT_PAIRED_EVIDENCE .*symbol=SBER .*pairs=1 ' \
<<< "$OUTPUT"

grep -q '^paired_baseline_superiority_required=1$' <<< "$OUTPUT"
grep -q '^v2_rank_used_for_edge_strength=0$' <<< "$OUTPUT"
grep -q '^thresholds_changed=0$' <<< "$OUTPUT"
grep -q '^net_first_logic_changed=0$' <<< "$OUTPUT"
grep -q '^db_writes_performed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=ACTIVE_CHALLENGER_EVIDENCE_PRIORITY_V3_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_ACTIVE_CHALLENGER_EVIDENCE_PRIORITY_V3_OK"
