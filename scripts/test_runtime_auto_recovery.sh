#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime_supervisor.py

grep -q "RUNTIME_SUPERVISOR_AUTO_RECOVERY" src/scripts/runtime_supervisor.py
grep -q "restart_unit" src/scripts/runtime_supervisor.py
grep -q "recoverable_units" src/scripts/runtime_supervisor.py
grep -q "RUNTIME_SUPERVISOR_AUTO_RECOVERY=1" systemd/runtime-supervisor.service

echo "OK: runtime auto recovery"
