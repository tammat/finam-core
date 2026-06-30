#!/usr/bin/env bash
set -euo pipefail
echo "=== TEST_RS_BOTTOM_FORWARD_DECAY_AUDIT_V1 ==="
python3 -m py_compile src/scripts/research/build_rs_bottom_forward_decay_audit_v1.py
python3 src/scripts/research/build_rs_bottom_forward_decay_audit_v1.py | tee /tmp/rs_bottom_forward_decay_audit_v1.log
grep -q "VERDICT=RS_BOTTOM_FORWARD_DECAY_AUDIT_READY" /tmp/rs_bottom_forward_decay_audit_v1.log
echo "TEST_RS_BOTTOM_FORWARD_DECAY_AUDIT_V1_OK"
