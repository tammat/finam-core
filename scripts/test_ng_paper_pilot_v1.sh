#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_PAPER_PILOT_V1_START"

python -m py_compile \
  src/finam_core/governance/ng_continuous_profile_gate_v1.py \
  src/scripts/runtime/run_ng_paper_pilot_v1.py

python src/scripts/runtime/run_ng_paper_pilot_v1.py \
  > /tmp/ng_paper_pilot_v1.out

grep -q "NG_PAPER_PILOT_V1_DECISION" /tmp/ng_paper_pilot_v1.out
grep -q "profile=NG_CONTINUOUS_SIDE_HOUR" /tmp/ng_paper_pilot_v1.out
grep -q "paper_only=1" /tmp/ng_paper_pilot_v1.out
grep -q "NG_PAPER_PILOT_V1_OK" /tmp/ng_paper_pilot_v1.out

echo "TEST_NG_PAPER_PILOT_V1_OK"
