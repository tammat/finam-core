from __future__ import annotations

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


class MarketSnapshotMapper:
    def build_snapshot(
        self,
        raw_record: dict,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> MarketSnapshotDTO:
        ts = snapshot_ts or datetime.now(UTC)

        return MarketSnapshotDTO(
            instrument=InstrumentDTO(
                symbol=raw_record["symbol"],
                instrument_name=raw_record["instrument_name"],
                exchange_code=raw_record["exchange_code"],
                asset_class=raw_record["asset_class"],
                currency_code=raw_record["currency_code"],
                isin=raw_record.get("isin"),
                figi=raw_record.get("figi"),
                is_active=bool(raw_record["is_active"]),
                source_version=raw_record["instrument_source_version"],
            ),
            contract=ContractSpecDTO(
                lot_size=Decimal(raw_record["lot_size"]),
                tick_size=Decimal(raw_record["tick_size"]),
                tick_value=Decimal(raw_record["tick_value"]),
                contract_multiplier=Decimal(raw_record["contract_multiplier"]),
                price_precision=int(raw_record["price_precision"]),
                min_price=None,
                max_price=None,
                source_version=raw_record["contract_source_version"],
            ),
            cost=TradingCostDTO(
                broker_code=broker_code,
                broker_fee_profile_code=raw_record["broker_fee_code"],
                exchange_fee_profile_code=raw_record["exchange_fee_code"],
                slippage_profile_code=raw_record["slippage_profile_code"],
                commission_fixed=Decimal(raw_record["commission_per_trade"]),
                commission_percent=Decimal(raw_record["commission_pct"]),
                exchange_fee_fixed=Decimal(raw_record["exchange_fee_per_trade"]),
                clearing_fee_fixed=Decimal(raw_record["clearing_fee_per_trade"]),
                slippage_fixed=Decimal(raw_record["slippage_per_trade"]),
                source_version="MARKET_SNAPSHOT_MAPPER_V1",
            ),
            tax=TaxProfileDTO(
                tax_profile_code=raw_record["tax_profile_code"],
                account_scope=account_scope,
                country_code="RU",
                tax_rate=Decimal(raw_record["tax_rate"]),
                tax_mode="PROFIT_ONLY",
                source_version="MARKET_SNAPSHOT_MAPPER_V1",
            ),
            session=TradingSessionDTO(
                session_code=f"{raw_record['exchange_code']}_MAIN",
                timezone="Europe/Moscow",
                open_time="10:00",
                close_time="18:45",
                has_auction=True,
                has_evening_session=False,
                is_weekend_trading_allowed=False,
                source_version="MARKET_SNAPSHOT_MAPPER_V1",
            ),
            eligibility=EligibilityDTO(
                market_universe_code=raw_record["eligibility_scope"],
                account_scope=account_scope,
                requires_qualified=(raw_record["eligibility_scope"] == "QUALIFIED"),
                requires_futures_access=(raw_record["asset_class"] == "FUTURES"),
                requires_options_access=False,
                requires_margin_access=False,
                is_allowed=True,
                source_version="MARKET_SNAPSHOT_MAPPER_V1",
            ),
            version=VersionInfoDTO(
                snapshot_uuid=uuid4(),
                market_model_version="MARKET_MODEL_V1",
                schema_version="v1",
                data_version="v1",
                snapshot_ts=ts,
                source_version="MARKET_SNAPSHOT_MAPPER_V1",
            ),
        )
