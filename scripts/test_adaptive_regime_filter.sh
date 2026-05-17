#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/risk/adaptive_regime_filter.py

python - <<'PY'
from finam_core.risk.adaptive_regime_filter import AdaptiveRegimeFilter

f = AdaptiveRegimeFilter(min_closed_trades=5, block_net_pnl_below=-10, reduce_net_pnl_below=0)

learning = f.evaluate("🟢 Накопление", closed_trades=2, net_pnl=-100, winrate=0)
assert learning.allowed is True
assert learning.action == "ALLOW_LEARNING"

blocked = f.evaluate("⚪ Обычная активность", closed_trades=20, net_pnl=-50, winrate=30)
assert blocked.allowed is False
assert blocked.action == "BLOCK"
assert blocked.multiplier == 0.0

allowed = f.evaluate("🚀 Запуск тренда", closed_trades=20, net_pnl=100, winrate=60)
assert allowed.allowed is True
assert allowed.action == "ALLOW"
assert allowed.multiplier == 1.0

print("OK: AdaptiveRegimeFilter")
PY
