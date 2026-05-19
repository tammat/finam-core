#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/portfolio_execution_planner.py \
  src/scripts/run_portfolio_execution_planner.py

python - <<'PY'
from finam_core.runtime.portfolio_execution_planner import (
    PortfolioExecutionPlanner,
)

planner = PortfolioExecutionPlanner()

plan = planner.build_plan(
    candidates=[
        {
            "symbol": "MGNT@MISX",
            "quality_score": 82,
            "quality_grade": "A",
            "expected_value": 176,
            "allocated_capital": 26000,
            "allocated_qty": 10,
            "correlation_group": "RETAIL",
        },
        {
            "symbol": "GAZP@MISX",
            "quality_score": 61,
            "quality_grade": "B",
            "expected_value": 110,
            "allocated_capital": 12000,
            "allocated_qty": 90,
            "correlation_group": "OIL_GAS",
        },
        {
            "symbol": "LKOH@MISX",
            "quality_score": 63,
            "quality_grade": "B",
            "expected_value": 140,
            "allocated_capital": 18000,
            "allocated_qty": 3,
            "correlation_group": "OIL_GAS",
        },
    ],
    max_execute=2,
)

assert len(plan) == 3
assert plan[0].decision == "EXECUTE"

print("OK: portfolio execution planner")
PY
