#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BR_LOSS_DECOMPOSITION_V1_START"

python -m py_compile src/scripts/analytics/build_br_loss_decomposition_v1.py

python src/scripts/analytics/build_br_loss_decomposition_v1.py --window-days 30 | tee /tmp/br_loss_decomposition_v1.out

grep -q "BR_LOSS_DECOMPOSITION_V1" /tmp/br_loss_decomposition_v1.out
grep -q "BR_LOSS_TOTAL" /tmp/br_loss_decomposition_v1.out
grep -q "BR_LOSS_DIRECTION" /tmp/br_loss_decomposition_v1.out
grep -q "BR_LOSS_HOUR" /tmp/br_loss_decomposition_v1.out
grep -q "BR_GOVERNANCE_HOUR_OVERLAY" /tmp/br_loss_decomposition_v1.out
grep -q "BR_LOSS_DECOMPOSITION_V1_OK" /tmp/br_loss_decomposition_v1.out

echo "TEST_BR_LOSS_DECOMPOSITION_V1_OK"
