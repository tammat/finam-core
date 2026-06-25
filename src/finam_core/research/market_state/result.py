from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MarketStateEvent:
    # Событие исследовательского pipeline.
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ClassifierResult:
    # Результат одного классификатора.
    group: str
    state: str
    confidence: float
    explanation_ru: str
    classifier_version: str


@dataclass(frozen=True)
class MarketStateResult:
    # Итоговый результат MarketStateEngine.
    symbol: str
    timeframe: str
    canonical_signature: str
    compact_signature: str
    quality: str
    confidence: float
    conflict_score: float
    explanation_tree_ru: list[str]
    classifier_results: tuple[ClassifierResult, ...] = field(default_factory=tuple)
    events: tuple[MarketStateEvent, ...] = field(default_factory=tuple)
    orders_sent: int = 0
    buy_sell_hold_decision: str = "NONE"
