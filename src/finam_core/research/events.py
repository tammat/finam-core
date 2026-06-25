from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResearchEvent:
    # Универсальное исследовательское событие.
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class MarketFeaturesReadyEvent:
    # Событие готовности рыночных признаков для Research Platform.
    symbol: str
    timeframe: str
    features: dict[str, Any]


@dataclass(frozen=True)
class MarketStateBuiltEvent:
    # Событие построенного состояния рынка.
    symbol: str
    timeframe: str
    canonical_signature: str
    compact_signature: str
    quality: str
    confidence: float
    payload: dict[str, Any]
