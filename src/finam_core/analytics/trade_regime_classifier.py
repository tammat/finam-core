from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradeRegime:
    hour: int
    market_session: str


def classify_trade_regime(ts: datetime) -> TradeRegime:
    # Простая первичная классификация по UTC-часу.
    # Это не финальный regime engine, а аналитический слой для edge validation.
    hour = int(ts.hour)

    if 6 <= hour < 10:
        market_session = "morning"
    elif 10 <= hour < 14:
        market_session = "day"
    elif 14 <= hour < 18:
        market_session = "evening"
    else:
        market_session = "off_hours"

    return TradeRegime(
        hour=hour,
        market_session=market_session,
    )
