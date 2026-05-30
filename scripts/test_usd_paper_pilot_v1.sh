#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_USD_PAPER_PILOT_V1_START"

python -m py_compile \
  src/finam_core/governance/usd_continuous_profile_gate_v1.py \
  src/scripts/runtime/run_usd_paper_pilot_v1.py

python src/scripts/runtime/run_usd_paper_pilot_v1.py \
  > /tmp/usd_paper_pilot_v1.out

grep -q "USD_PAPER_PILOT_V1_DECISION" /tmp/usd_paper_pilot_v1.out
grep -q "profile=USD_CONTINUOUS_SIDE_HOUR" /tmp/usd_paper_pilot_v1.out
grep -q "paper_only=1" /tmp/usd_paper_pilot_v1.out
grep -q "USD_PAPER_PILOT_V1_OK" /tmp/usd_paper_pilot_v1.out

echo "TEST_USD_PAPER_PILOT_V1_OK"
