from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from finam_core.data.moex_candle_provider import MoexCandleProvider
from finam_core.data.moex_symbol_resolver import MoexSymbolResolver


@dataclass(frozen=True)
class ReplayBarEvent:
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
    source: str = "moex"


class ExternalReplayAdapter:
    """Русский комментарий: адаптер внешних свечей MOEX в replay event stream."""

    def __init__(
        self,
        candle_provider: MoexCandleProvider | None = None,
        resolver: MoexSymbolResolver | None = None,
    ) -> None:
        self.candle_provider = candle_provider or MoexCandleProvider()
        self.resolver = resolver or MoexSymbolResolver()

    def load_events(
        self,
        *,
        symbol: str,
        timeframe: str,
        date_from: str,
        date_to: str,
    ) -> list[ReplayBarEvent]:

        resolved = self.resolver.resolve(symbol)

        candles = self.candle_provider.load_candles(
            symbol=resolved.symbol,
            board=resolved.board,
            engine=resolved.engine,
            market=resolved.market,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to,
        )

        events: list[ReplayBarEvent] = []

        for c in candles:
            events.append(
                ReplayBarEvent(
                    symbol=symbol,
                    ts=datetime.fromisoformat(c.begin),
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    volume=c.volume,
                    timeframe=timeframe,
                )
            )

        return events
