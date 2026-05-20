#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_synthetic_protective_trigger.py

grep -q "SYNTHETIC_PROTECTIVE_FORCE_TRIGGER" src/scripts/run_synthetic_protective_trigger.py
grep -q "SYNTH_PROTECTIVE_FORCE_TRIGGER_ACTIVE" src/scripts/run_synthetic_protective_trigger.py

echo "OK: synthetic protective force trigger"
