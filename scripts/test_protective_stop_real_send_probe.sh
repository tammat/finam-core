#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_protective_stop_real_send_probe.py

grep -q "PROTECTIVE_STOP_REAL_SEND_PROBE_REAL_ACK" src/scripts/run_protective_stop_real_send_probe.py
grep -q "PROTECTIVE_REAL_SEND_PROBE_ARMED" src/scripts/run_protective_stop_real_send_probe.py
grep -q "dry_stop_" src/scripts/run_protective_stop_real_send_probe.py
grep -q "place_stop_order" src/scripts/run_protective_stop_real_send_probe.py

echo "OK: protective stop real send probe"
