#!/usr/bin/env bash
set -euo pipefail

test -f systemd/runtime-state-snapshot.service
test -f systemd/runtime-state-snapshot.timer

grep -q "save_runtime_state_snapshot.py" systemd/runtime-state-snapshot.service
grep -q "OnUnitActiveSec=5min" systemd/runtime-state-snapshot.timer
grep -q "runtime-state-snapshot.timer" scripts/install_runtime_state_snapshot_timer.sh

echo "OK: runtime state snapshot timer templates"
