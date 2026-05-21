#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/portfolio_governance_refresh.py \
  src/scripts/send_runtime_governance_alert.py

grep -q "send_runtime_governance_alert.py" src/scripts/portfolio_governance_refresh.py
grep -q "PORTFOLIO_GOVERNANCE_ALERT_FAILED" src/scripts/portfolio_governance_refresh.py

echo "TEST_PORTFOLIO_GOVERNANCE_REFRESH_ALERT_COMPILE_OK"
