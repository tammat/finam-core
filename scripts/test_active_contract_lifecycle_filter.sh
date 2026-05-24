#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/research/active_contract_lifecycle_filter.py

python - <<'PY'
from finam_core.research.active_contract_lifecycle_filter import is_active_contract_edge_confirmed

bad = is_active_contract_edge_confirmed(
    root_symbol="NG",
    active_symbol="NGM6@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    trades=28,
    avg_net_pnl=-0.0067,
    win_rate=0.50,
)
assert bad.allowed is False
assert bad.reason == "active_contract_not_enough_trades"

ok = is_active_contract_edge_confirmed(
    root_symbol="NG",
    active_symbol="NGM6@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    trades=40,
    avg_net_pnl=0.01,
    win_rate=0.52,
)
assert ok.allowed is True

print("ACTIVE_CONTRACT_LIFECYCLE_FILTER_OK")
PY
