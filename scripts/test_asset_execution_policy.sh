#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
import os
from finam_core.execution.asset_execution_policy import AssetExecutionPolicy

p = AssetExecutionPolicy()

os.environ["REAL_TRADING_ENABLED"] = "0"
d = p.decide("SBERP@MISX")
assert d.allowed is False
assert d.reason == "real_trading_disabled"

os.environ["REAL_TRADING_ENABLED"] = "1"
os.environ["REAL_STOCK_TRADING_ENABLED"] = "1"
os.environ["REAL_STOCK_ALLOWLIST"] = "SBERP,LKOH"

d = p.decide("SBERP@MISX")
assert d.allowed is True
assert d.asset_class == "STOCK"

d = p.decide("OZON@MISX")
assert d.allowed is False
assert "stock_not_in_allowlist" in d.reason

d = p.decide("BRM6@RTSX")
assert d.allowed is False
assert d.mode == "TELEGRAM_ONLY"

d = p.decide("SU26243RMFS4")
assert d.allowed is False
assert d.asset_class == "BOND"

print("ASSET_EXECUTION_POLICY_OK")
PY
