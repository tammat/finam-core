#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.drawdown_summary import build_drawdown_summary

summary = build_drawdown_summary([10, 5, -3, -4, -8, 2, 3, -1])

assert summary.trades == 8
assert summary.final_pnl == 4
assert summary.max_drawdown == -15
assert summary.max_drawdown_trade_index == 5
assert summary.max_win_streak == 2
assert summary.max_loss_streak == 3
assert summary.avg_win == 5
assert summary.avg_loss == 4
assert summary.payoff_ratio == 1.25

print("TEST_DRAWDOWN_SUMMARY_OK")
PY
