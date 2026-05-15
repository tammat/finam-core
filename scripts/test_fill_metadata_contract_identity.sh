#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/contracts/contract_identity_resolver.py \
  src/finam_core/execution/fill_metadata_factory.py

python - <<'PY'
from finam_core.execution.fill_metadata_factory import FillMetadataFactory

br = FillMetadataFactory.build(
    intent={
        "symbol": "BRM6@RTSX",
        "signal_id": "sig-br",
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "horizon": "INTRADAY",
        "timeframe": "LIVE",
    },
    market_state={},
    raw_payload={},
)

assert br["signal_id"] == "sig-br"
assert br["strategy"] == "BR_CONSERVATIVE_BREAKOUT"
assert br["root_symbol"] == "BR"
assert br["continuous_symbol"] == "BR_CONT"
assert br["futures_month_code"] == "M"
assert br["futures_year_code"] == "6"
assert br["is_futures"] is True
assert br["venue"] == "RTSX"

ng = FillMetadataFactory.build(
    intent={"symbol": "NGH6@RTSX", "strategy": "NG_VOLATILITY_BREAKOUT"},
    market_state={},
    raw_payload={},
)

assert ng["root_symbol"] == "NG"
assert ng["continuous_symbol"] == "NG_CONT"
assert ng["futures_month_code"] == "H"
assert ng["futures_year_code"] == "6"

usd = FillMetadataFactory.build(
    intent={"symbol": "USDRUBF@RTSX", "strategy": "USDRUB_REGIME"},
    market_state={},
    raw_payload={},
)

assert usd["root_symbol"] == "USDRUB"
assert usd["continuous_symbol"] == "USDRUB_CONT"
assert usd["futures_month_code"] == "F"
assert usd["futures_year_code"] == ""

sber = FillMetadataFactory.build(
    intent={"symbol": "SBER@MISX", "strategy": "TREND_PULLBACK_EQUITY"},
    market_state={},
    raw_payload={},
)

assert sber["root_symbol"] == "SBER"
assert sber["continuous_symbol"] == "SBER"
assert sber["is_futures"] is False
assert sber["venue"] == "MISX"

print("OK: FillMetadataFactory adds futures/continuous contract identity")
PY
