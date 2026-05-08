# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from finam_core.analytics.futures_pnl import FuturesPnlCalculator


@dataclass(frozen=True)
class TradeOutcome:
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    stop_loss: float
    take_profit: float
    pnl: float
    pnl_pct: float
    rr_planned: float
    r_multiple: float
    result: str
    reason: str


class TradeOutcomeReporter:
    """
    Русский комментарий:
    Анализирует завершённую сделку и отправляет отчёт.
    Заявки не отправляет.
    """

    def __init__(self, notifier) -> None:
        self.notifier = notifier

    def analyze(
        self,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        qty: float,
        stop_loss: float,
        take_profit: float,
        reason: str = "",
    ) -> TradeOutcome:
        side = str(side).upper()
        entry_price = float(entry_price)
        exit_price = float(exit_price)
        qty = float(qty)
        stop_loss = float(stop_loss)
        take_profit = float(take_profit)

        futures_calc = FuturesPnlCalculator()
        pnl = futures_calc.pnl(
            symbol=symbol,
            side=side,
            entry=entry_price,
            exit=exit_price,
            qty=qty,
        )

        risk_money = futures_calc.risk_money(
            symbol=symbol,
            side=side,
            entry=entry_price,
            stop=stop_loss,
            qty=qty,
        )

        if side == "BUY":
            reward_per_unit = abs(take_profit - entry_price)
            risk_per_unit = abs(entry_price - stop_loss)
        else:
            reward_per_unit = abs(entry_price - take_profit)
            risk_per_unit = abs(stop_loss - entry_price)

        pnl_pct = (pnl / (entry_price * qty) * 100.0) if entry_price > 0 and qty > 0 else 0.0
        rr_planned = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0.0
        r_multiple = (pnl / risk_money) if risk_money > 0 else 0.0

        if pnl > 0:
            result = "PROFIT"
        elif pnl < 0:
            result = "LOSS"
        else:
            result = "BREAKEVEN"

        return TradeOutcome(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            qty=qty,
            stop_loss=stop_loss,
            take_profit=take_profit,
            pnl=round(pnl, 4),
            pnl_pct=round(pnl_pct, 4),
            rr_planned=round(rr_planned, 4),
            r_multiple=round(r_multiple, 4),
            result=result,
            reason=reason,
        )

    def send_outcome(self, outcome: TradeOutcome) -> bool:
        text = (
            "📊 ИТОГ СДЕЛКИ\n\n"
            f"Инструмент: {outcome.symbol}\n"
            f"Сторона: {outcome.side}\n"
            f"Кол-во: {outcome.qty}\n\n"
            f"Вход: {outcome.entry_price:.4f}\n"
            f"Выход: {outcome.exit_price:.4f}\n"
            f"Stop: {outcome.stop_loss:.4f}\n"
            f"Take: {outcome.take_profit:.4f}\n\n"
            f"P&L: {outcome.pnl:.4f}\n"
            f"P&L %: {outcome.pnl_pct:.2f}%\n"
            f"Плановый RR: {outcome.rr_planned:.2f}\n"
            f"Факт R: {outcome.r_multiple:.2f}R\n"
            f"Результат: {outcome.result}\n\n"
            f"Анализ: {outcome.reason}"
        )

        if hasattr(self.notifier, "send"):
            self.notifier.send(text)
            return True

        if hasattr(self.notifier, "send_text"):
            return bool(self.notifier.send_text(text))

        return False
