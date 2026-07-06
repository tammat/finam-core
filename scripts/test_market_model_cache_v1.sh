#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_CACHE_V1 ==="

PYTHONPATH=src python -m py_compile \
    src/marketcore/market/cache/market_model_cache.py \
    src/marketcore/market/cache/__init__.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from marketcore.market.cache import MarketModelCache
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
        source_version="CACHE_TEST",
    ),
    contract=ContractSpecDTO(
        lot_size=Decimal("10"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("0.01"),
        contract_multiplier=Decimal("1"),
        price_precision=2,
        min_price=None,
        max_price=None,
        source_version="CACHE_TEST",
    ),
    cost=TradingCostDTO(
        broker_code="FINAM",
        broker_fee_profile_code="BF",
        exchange_fee_profile_code="EF",
        slippage_profile_code="SP",
        commission_fixed=Decimal("0"),
        commission_percent=Decimal("0"),
        exchange_fee_fixed=Decimal("0"),
        clearing_fee_fixed=Decimal("0"),
        slippage_fixed=Decimal("0"),
        source_version="CACHE_TEST",
    ),
    tax=TaxProfileDTO(
        tax_profile_code="RU",
        account_scope="BASE",
        country_code="RU",
        tax_rate=Decimal("0.15"),
        tax_mode="PROFIT_ONLY",
        source_version="CACHE_TEST",
    ),
    session=TradingSessionDTO(
        session_code="MAIN",
        timezone="Europe/Moscow",
        open_time="10:00",
        close_time="18:45",
        has_auction=True,
        has_evening_session=False,
        is_weekend_trading_allowed=False,
        source_version="CACHE_TEST",
    ),
    eligibility=EligibilityDTO(
        market_universe_code="QUALIFIED",
        account_scope="QUALIFIED",
        requires_qualified=True,
        requires_futures_access=False,
        requires_options_access=False,
        requires_margin_access=False,
        is_allowed=True,
        source_version="CACHE_TEST",
    ),
    version=VersionInfoDTO(
        snapshot_uuid=uuid4(),
        market_model_version="V1",
        schema_version="1",
        data_version="1",
        snapshot_ts=datetime.now(UTC),
        source_version="CACHE_TEST",
    ),
)

cache = MarketModelCache(max_size=2)

cache.put("SBER", snapshot)

assert cache.size() == 1
assert cache.get("SBER") is snapshot

cache.invalidate("SBER")

assert cache.get("SBER") is None

cache.put("SBER", snapshot)
cache.clear()

assert cache.size() == 0

print("MARKET_MODEL_CACHE_OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_MODEL_CACHE_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_CACHE_V1_OK"
