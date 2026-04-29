#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src CORR_BUCKET_LIMIT=0.35 python - <<'PY'
from finam_core.risk.correlation_risk import CorrelationRiskEngine

e = CorrelationRiskEngine()

assert e.bucket_for_symbol("BRM6@RTSX") == "energy"
assert e.bucket_for_symbol("NGH6@RTSX") == "energy"
assert e.bucket_for_symbol("USDRUB@RTSX") == "fx"
assert e.bucket_for_symbol("GAZP@MISX") == "equity"

ok = e.evaluate(
    symbol="BRM6@RTSX",
    portfolio_value=100_000,
    current_bucket_exposure=10_000,
    new_trade_value=5_000,
)
assert ok.allowed is True
assert ok.reason == "ok"

bad = e.evaluate(
    symbol="NGH6@RTSX",
    portfolio_value=100_000,
    current_bucket_exposure=34_000,
    new_trade_value=2_000,
)
assert bad.allowed is False
assert bad.reason == "bucket_exposure_exceeded"
assert bad.bucket == "energy"

invalid = e.evaluate(
    symbol="BRM6@RTSX",
    portfolio_value=0,
    current_bucket_exposure=0,
    new_trade_value=1,
)
assert invalid.allowed is False
assert invalid.reason == "invalid_portfolio_value"

print("OK correlation_risk")
PY
