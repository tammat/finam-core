from __future__ import annotations

from dataclasses import dataclass

from marketcore.market.dto.contract_spec import ContractSpecDTO
from marketcore.market.dto.eligibility import EligibilityDTO
from marketcore.market.dto.instrument import InstrumentDTO
from marketcore.market.dto.tax_profile import TaxProfileDTO
from marketcore.market.dto.trading_cost import TradingCostDTO
from marketcore.market.dto.trading_session import TradingSessionDTO
from marketcore.market.dto.version_info import VersionInfoDTO


@dataclass(frozen=True, slots=True)
class MarketSnapshotDTO:
    instrument: InstrumentDTO
    contract: ContractSpecDTO
    cost: TradingCostDTO
    tax: TaxProfileDTO
    session: TradingSessionDTO
    eligibility: EligibilityDTO
    version: VersionInfoDTO
