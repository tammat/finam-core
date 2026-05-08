# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FuturesSignal:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    confidence: float
    reason: str


class FinamFuturesSignalRadar:
    """
    Русский комментарий:
    Только расчёт торговых сигналов по фьючерсам/валюте.
    Реальные заявки НЕ отправляет.
    """

    def __init__(
        self,
        atr_mult_stop: float = 1.5,
        atr_mult_take: float = 2.0,
    ) -> None:
        self.atr_mult_stop = float(atr_mult_stop)
        self.atr_mult_take = float(atr_mult_take)

    def build_signal(
        self,
        symbol: str,
        last: float,
        atr: float,
        trend_score: float,
    ) -> FuturesSignal | None:
        if last <= 0 or atr <= 0:
            return None

        if abs(trend_score) < 0.2:
            return None

        side = "BUY" if trend_score > 0 else "SELL"

        if side == "BUY":
            entry = round(last, 4)
            stop = round(last - atr * self.atr_mult_stop, 4)
            take = round(last + atr * self.atr_mult_take, 4)
        else:
            entry = round(last, 4)
            stop = round(last + atr * self.atr_mult_stop, 4)
            take = round(last - atr * self.atr_mult_take, 4)

        return FuturesSignal(
            symbol=str(symbol),
            side=side,
            entry=entry,
            stop_loss=stop,
            take_profit=take,
            confidence=round(min(abs(trend_score), 1.0), 4),
            reason="finam_futures_signal",
        )
