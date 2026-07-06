from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TradingCostDTO:
    broker_code: str
    broker_fee_profile_code: str
    exchange_fee_profile_code: str
    slippage_profile_code: str
    commission_fixed: Decimal
    commission_percent: Decimal
    exchange_fee_fixed: Decimal
    clearing_fee_fixed: Decimal
    slippage_fixed: Decimal
    source_version: str
