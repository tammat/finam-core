#!/usr/bin/env bash
set -euo pipefail

test -f systemd/policy-rotation.service
test -f systemd/policy-rotation.timer

grep -q "rotate_active_policy.py" systemd/policy-rotation.service
grep -q "OnUnitActiveSec" systemd/policy-rotation.timer

echo "OK: policy rotation timer compile"
