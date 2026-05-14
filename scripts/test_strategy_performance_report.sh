#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/strategy_performance_report.py

python src/scripts/strategy_performance_report.py --dry-run \
| grep -E "SIGNALS_BY_STRATEGY|RISK_DECISIONS|TRADES_BY_SYMBOL_SOURCE|CLOSED_TRADES_PERFORMANCE|REJECTION_REASONS|RECENT_TRADES" >/dev/null

echo "OK: strategy performance report compile and dry-run"
