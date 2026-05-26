#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/build_strategy_scorecard.py

grep -q "CREATE OR REPLACE VIEW strategy_scorecard_v1" sql/create_strategy_scorecard_v1.sql
grep -q "profit_factor" sql/create_strategy_scorecard_v1.sql
grep -q "payoff_ratio" sql/create_strategy_scorecard_v1.sql
grep -q "expectancy" sql/create_strategy_scorecard_v1.sql

python src/scripts/build_strategy_scorecard.py --help | grep -q -- "--continuous-symbol"

echo "STRATEGY_SCORECARD_V1_COMPILE_OK"
