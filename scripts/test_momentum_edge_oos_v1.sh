#!/usr/bin/env bash
set -euo pipefail

PYTHONPYCACHEPREFIX=/tmp/momentum_edge_oos_pycache PYTHONPATH=src \
  .venv/bin/python -m py_compile src/scripts/validate_momentum_edge_oos_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python src/scripts/validate_momentum_edge_oos_v1.py \
  | tee /tmp/momentum_edge_oos_v1.log

grep -q '^oos_bars=[1-9]' /tmp/momentum_edge_oos_v1.log
grep -q '^folds_passed=' /tmp/momentum_edge_oos_v1.log
grep -q '^runtime_changed=0$' /tmp/momentum_edge_oos_v1.log
grep -q '^orders_changed=0$' /tmp/momentum_edge_oos_v1.log
grep -q '^micro_live_allowed=0$' /tmp/momentum_edge_oos_v1.log
grep -Eq '^VERDICT=MOMENTUM_EDGE_OOS_(PASS|FAIL)$' /tmp/momentum_edge_oos_v1.log

business_verdict=$(grep '^VERDICT=MOMENTUM_EDGE_OOS_' /tmp/momentum_edge_oos_v1.log | cut -d= -f2)
echo "business_verdict=$business_verdict"
echo "VERDICT=TEST_MOMENTUM_EDGE_OOS_CLASSIFICATION_V1_OK"
