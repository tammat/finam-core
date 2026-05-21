#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.equity_curve import build_equity_curve

points = build_equity_curve([10, -5, 3, -20, 7])

assert len(points) == 5

assert points[0].cumulative_pnl == 10
assert points[1].drawdown == -5
assert points[2].cumulative_pnl == 8
assert points[3].drawdown == -22
assert points[4].cumulative_pnl == -5

print("TEST_EQUITY_CURVE_OK")
PY
