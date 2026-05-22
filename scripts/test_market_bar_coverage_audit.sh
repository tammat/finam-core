#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_market_bar_coverage_audit.py
grep -q "strategy_market_bar_coverage" src/scripts/build_market_bar_coverage_audit.py
grep -q "MARKET_BAR_COVERAGE_AUDIT_OK" src/scripts/build_market_bar_coverage_audit.py

echo "TEST_MARKET_BAR_COVERAGE_AUDIT_OK"
