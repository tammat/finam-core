#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/recover_futures_fill_context.py

grep -q "FUTURES_FILL_CONTEXT_RECOVERY_SUMMARY" src/scripts/recover_futures_fill_context.py
grep -q "BR_CONSERVATIVE_BREAKOUT" src/scripts/recover_futures_fill_context.py
grep -q "NG_CONSERVATIVE_SETUP" src/scripts/recover_futures_fill_context.py
grep -q "USD_INTRADAY_REGIME" src/scripts/recover_futures_fill_context.py

echo "TEST_RECOVER_FUTURES_FILL_CONTEXT_OK"
