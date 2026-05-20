#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_synthetic_protective_trigger.py

grep -q "SYNTH_PROTECTIVE_STATE" src/scripts/run_synthetic_protective_trigger.py
grep -q "SYNTH_PROTECTIVE_INTENT_CREATED" src/scripts/run_synthetic_protective_trigger.py
grep -q "synthetic_protective_real_sell" src/scripts/run_synthetic_protective_trigger.py
grep -q "synthetic_protective_shadow_sell" src/scripts/run_synthetic_protective_trigger.py

echo "OK: synthetic protective trigger"
