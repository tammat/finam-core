#!/usr/bin/env bash
set -euo pipefail

test -f systemd/runtime-supervisor.service
test -f systemd/runtime-supervisor.timer

grep -q "runtime_supervisor.py" systemd/runtime-supervisor.service
grep -q "RUNTIME_SUPERVISOR_SEND_OK=0" systemd/runtime-supervisor.service
grep -q "OnUnitActiveSec=10min" systemd/runtime-supervisor.timer
grep -q "runtime-supervisor.timer" scripts/install_runtime_supervisor_timer.sh

echo "OK: runtime supervisor timer templates"
