# src/finam_core/analytics/trade_journal.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class TradeRow:
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0


@dataclass
class TradeJournalSummary:
    trades_count: int
    closed_cycles: int
    wins: int
    losses: int
    total_pnl: float
    avg_pnl: float
    winrate: float


class TradeJournal:
    """
    Русский коммент: журнал сделок для расчёта PnL по парным входам/выходам.
    Пока поддерживает последовательные циклы: BUY→SELL и SELL→BUY.
    """

    def summarize(self, trades: Iterable[TradeRow]) -> TradeJournalSummary:
        rows = list(trades)
        open_trade: TradeRow | None = None
        pnls: list[float] = []

        for t in rows:
            side = str(t.side).upper()

            if open_trade is None:
                open_trade = t
                continue

            open_side = str(open_trade.side).upper()

            # LONG: BUY -> SELL
            if open_side == "BUY" and side == "SELL":
                qty = min(abs(open_trade.qty), abs(t.qty))
                pnl = (t.price - open_trade.price) * qty
                pnl -= open_trade.commission + t.commission
                pnls.append(pnl)
                open_trade = None
                continue

            # SHORT: SELL -> BUY
            if open_side == "SELL" and side == "BUY":
                qty = min(abs(open_trade.qty), abs(t.qty))
                pnl = (open_trade.price - t.price) * qty
                pnl -= open_trade.commission + t.commission
                pnls.append(pnl)
                open_trade = None
                continue

            # Если направление не закрывает позицию — начинаем новый цикл.
            open_trade = t

        wins = sum(1 for x in pnls if x > 0)
        losses = sum(1 for x in pnls if x < 0)
        total = sum(pnls)
        cycles = len(pnls)

        return TradeJournalSummary(
            trades_count=len(rows),
            closed_cycles=cycles,
            wins=wins,
            losses=losses,
            total_pnl=total,
            avg_pnl=(total / cycles if cycles else 0.0),
            winrate=(wins / cycles if cycles else 0.0),
        )
