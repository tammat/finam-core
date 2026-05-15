#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/trade_gate_service.py

python - <<'PY'
from finam_core.runtime.trade_gate_service import TradeGateService

svc = TradeGateService(
    base_cooldown_sec=1,
    max_trades_per_hour=2,
    max_trades_per_symbol=1,
)

d = svc.cooldown_allows("BRM6@RTSX", price=100, atr=1)
assert d.allowed is True, d

a = svc.account_trade("BRM6@RTSX")
assert a.allowed is True
assert "trade_accounted" in a.reason

d = svc.cooldown_allows("BRM6@RTSX", price=100, atr=1)
assert d.allowed is False
assert "cooldown_block" in d.reason

d = svc.trade_limit_allows("BRM6@RTSX")
assert d.allowed is False
assert "trade_limit_block_symbol" in d.reason

print("OK: TradeGateService cooldown/trade-limit works")
PY
