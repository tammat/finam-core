#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime_supervisor.py

grep -q "finam-radar-chain.timer" src/scripts/runtime_supervisor.py
grep -q "signal-lifecycle-monitor.timer" src/scripts/runtime_supervisor.py
grep -q "RUNTIME_SUPERVISOR_OK" src/scripts/runtime_supervisor.py

echo "OK: runtime supervisor compile"
