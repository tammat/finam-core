#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_active_challenger_evidence_trajectory_v1.py"

echo "=== TEST ACTIVE CHALLENGER EVIDENCE TRAJECTORY V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q \
'^TRAJECTORY_ROW .*symbol=SBERP .*candidate=CONFIRM_1_S1.8_R1.8 ' \
<<< "$OUTPUT"

grep -q \
'^TRAJECTORY_ROW .*symbol=SBER .*candidate=IMMEDIATE_S1.5_R1.6 ' \
<<< "$OUTPUT"

grep -q '^targets=2$' <<< "$OUTPUT"
grep -q '^trajectory_snapshot_only=1$' <<< "$OUTPUT"
grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=ACTIVE_CHALLENGER_EVIDENCE_TRAJECTORY_V1_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_ACTIVE_CHALLENGER_EVIDENCE_TRAJECTORY_V1_OK"
