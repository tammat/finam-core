#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_runtime_control_alerts.py

echo "OK: runtime control alerts compile"
