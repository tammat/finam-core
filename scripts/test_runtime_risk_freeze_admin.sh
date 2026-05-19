#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime_risk_freeze_admin.py

grep -q "RUNTIME_RISK_FREEZE_STATUS" src/scripts/runtime_risk_freeze_admin.py
grep -q "RUNTIME_RISK_FREEZE_CLEARED" src/scripts/runtime_risk_freeze_admin.py
grep -q "manual_clear_after_review" src/scripts/runtime_risk_freeze_admin.py

echo "OK: runtime risk freeze admin"
