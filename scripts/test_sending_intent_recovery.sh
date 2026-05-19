#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_sending_intent_recovery.py

grep -q "SENDING_INTENT_RECOVERY_RECONCILE_REQUIRED" src/scripts/run_sending_intent_recovery.py
grep -q "RECONCILE_REQUIRED" src/scripts/run_sending_intent_recovery.py
grep -q "SENDING" src/scripts/run_sending_intent_recovery.py

echo "OK: sending intent recovery"
