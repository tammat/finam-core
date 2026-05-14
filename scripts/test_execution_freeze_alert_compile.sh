#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_execution_freeze_alert.py

echo "OK: execution freeze alert compiles"
