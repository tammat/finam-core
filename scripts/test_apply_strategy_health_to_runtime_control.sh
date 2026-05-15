#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/apply_strategy_health_to_runtime_control.py \
  src/finam_core/analytics/strategy_health_engine.py \
  src/finam_core/analytics/adaptive_strategy_weighting_engine.py

python src/scripts/apply_strategy_health_to_runtime_control.py --dry-run --days 30 --min-trades 3 >/tmp/apply_strategy_health_dry_run.tsv

grep -E "symbol|strategy|\(0 rows\)|HEALTHY|BLOCKED|WATCH" /tmp/apply_strategy_health_dry_run.tsv >/dev/null

echo "OK: применение health/weighting к strategy_runtime_control компилируется"
