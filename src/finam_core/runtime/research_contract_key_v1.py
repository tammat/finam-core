from __future__ import annotations

from dataclasses import dataclass

from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver


@dataclass(frozen=True)
class ResearchContractKeyV1:
    execution_mode: str
    normalized_symbol: str
    strategy: str
    timeframe: str
    side: str
    session_name: str
    regime_code: str


def normalize_research_contract_key_v1(
    *,
    symbol: str,
    strategy: str | None,
    timeframe: str | None,
    side: str | None,
    session_name: str | None,
    regime: str | None,
    execution_mode: str = "PAPER",
) -> ResearchContractKeyV1:
    """Канонический ключ исследования, квоты и строгого runtime-правила."""
    identity = ContractIdentityResolver.resolve(str(symbol or "").upper().strip())
    strategy_norm = str(strategy or "UNKNOWN").upper().strip()
    timeframe_norm = str(timeframe or "UNKNOWN").upper().strip()
    side_norm = str(side or "UNKNOWN").upper().strip()

    if side_norm == "LONG":
        side_norm = "BUY"
    elif side_norm == "SHORT":
        side_norm = "SELL"

    # BR_CONSERVATIVE_BREAKOUT формируется на M5. LIVE был транспортной меткой,
    # а не таймфреймом доказательств.
    if strategy_norm == "BR_CONSERVATIVE_BREAKOUT" and timeframe_norm in {
        "", "LIVE", "UNKNOWN", "UNKNOWN_TIMEFRAME"
    }:
        timeframe_norm = "M5"

    normalized_symbol = identity.continuous if identity.is_futures else identity.symbol
    return ResearchContractKeyV1(
        execution_mode=str(execution_mode or "PAPER").upper().strip(),
        normalized_symbol=normalized_symbol,
        strategy=strategy_norm,
        timeframe=timeframe_norm or "UNKNOWN",
        side=side_norm,
        session_name=str(session_name or "UNKNOWN").strip(),
        regime_code=str(regime or "UNKNOWN").strip().lower(),
    )
