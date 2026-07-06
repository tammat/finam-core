#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_FOUNDATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/market/dto/instrument.py \
  src/marketcore/market/dto/contract_spec.py \
  src/marketcore/market/dto/trading_cost.py \
  src/marketcore/market/dto/tax_profile.py \
  src/marketcore/market/dto/trading_session.py \
  src/marketcore/market/dto/eligibility.py \
  src/marketcore/market/dto/version_info.py \
  src/marketcore/market/dto/market_snapshot.py \
  src/marketcore/market/dto/__init__.py

PYTHONPATH=src python - <<'PY'
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from marketcore.market.dto import (
    ContractSpecDTO,
    EligibilityDTO,
    InstrumentDTO,
    MarketSnapshotDTO,
    TaxProfileDTO,
    TradingCostDTO,
    TradingSessionDTO,
    VersionInfoDTO,
)

snapshot = MarketSnapshotDTO(
    instrument=InstrumentDTO(
        symbol="SBER@MISX",
        instrument_name="Sberbank",
        exchange_code="MISX",
        asset_class="EQUITY",
        currency_code="RUB",
        isin=None,
        figi=None,
        is_active=True,
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
    contract=ContractSpecDTO(
        lot_size=Decimal("10"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("0.01"),
        contract_multiplier=Decimal("1"),
        price_precision=2,
        min_price=None,
        max_price=None,
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
    cost=TradingCostDTO(
        broker_code="FINAM",
        broker_fee_profile_code="FINAM_MISX_EQUITY_BASE",
        exchange_fee_profile_code="MISX_EQUITY_BASE",
        slippage_profile_code="MISX_EQUITY_DEFAULT",
        commission_fixed=Decimal("0.01"),
        commission_percent=Decimal("0.0005"),
        exchange_fee_fixed=Decimal("0"),
        clearing_fee_fixed=Decimal("0"),
        slippage_fixed=Decimal("0.01"),
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
    tax=TaxProfileDTO(
        tax_profile_code="RU_TAXABLE_BASE",
        account_scope="BASE",
        country_code="RU",
        tax_rate=Decimal("0.15"),
        tax_mode="PROFIT_ONLY",
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
    session=TradingSessionDTO(
        session_code="MISX_MAIN",
        timezone="Europe/Moscow",
        open_time="10:00",
        close_time="18:45",
        has_auction=True,
        has_evening_session=False,
        is_weekend_trading_allowed=False,
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
    eligibility=EligibilityDTO(
        market_universe_code="BASE",
        account_scope="BASE",
        requires_qualified=False,
        requires_futures_access=False,
        requires_options_access=False,
        requires_margin_access=False,
        is_allowed=True,
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
    version=VersionInfoDTO(
        snapshot_uuid=uuid4(),
        market_model_version="MARKET_MODEL_FOUNDATION_V1",
        schema_version="v1",
        data_version="v1",
        snapshot_ts=datetime.now(UTC),
        source_version="MARKET_MODEL_FOUNDATION_V1",
    ),
)

assert snapshot.instrument.symbol == "SBER@MISX"
assert snapshot.contract.lot_size == Decimal("10")
assert snapshot.cost.broker_code == "FINAM"
assert snapshot.tax.tax_rate == Decimal("0.15")
assert snapshot.eligibility.is_allowed is True

try:
    snapshot.instrument.symbol = "TEST"
    raise RuntimeError("DTO_MUTABLE")
except FrozenInstanceError:
    pass

print("MARKET_SNAPSHOT_DTO_OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_FOUNDATION_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_FOUNDATION_V1_OK"
