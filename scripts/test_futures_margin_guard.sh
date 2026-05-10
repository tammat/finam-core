#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export FUTURES_MAX_MARGIN_UTILIZATION=0.50
export FUTURES_MARGIN_BRM6=25000
export FUTURES_MARGIN_NGH6=5000

python - <<'PY'
from finam_core.futures.futures_margin_guard import FuturesMarginGuard

g = FuturesMarginGuard()

ok = g.check(
    symbol="BRM6@RTSX",
    qty=1,
    equity=200000,
    used_margin_before=50000,
)
assert ok.allowed is True, ok
assert ok.reason == "futures_margin_ok", ok
assert ok.required_margin == 25000.0, ok

block = g.check(
    symbol="BRM6@RTSX",
    qty=3,
    equity=200000,
    used_margin_before=50000,
)
assert block.allowed is False, block
assert block.reason == "futures_margin_utilization_limit", block

ng_ok = g.check(
    symbol="NGH6@RTSX",
    qty=5,
    equity=200000,
    used_margin_before=50000,
)
assert ng_ok.allowed is True, ng_ok

stock = g.check(
    symbol="SBER@MISX",
    qty=100,
    equity=200000,
    used_margin_before=50000,
)
assert stock.allowed is True, stock
assert stock.reason == "not_futures_symbol", stock

zero_equity = g.check(
    symbol="BRM6@RTSX",
    qty=1,
    equity=0,
    used_margin_before=0,
)
assert zero_equity.allowed is False, zero_equity
assert zero_equity.reason == "equity_not_positive", zero_equity

print("FUTURES_MARGIN_GUARD_OK")
PY
