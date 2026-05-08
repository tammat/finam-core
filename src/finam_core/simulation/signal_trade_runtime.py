# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from finam_core.simulation.signal_paper_trade_tracker import SignalPaperTradeTracker
from finam_core.analytics.trade_outcome_reporter import TradeOutcomeReporter
from finam_core.notifications.notification_router import NotificationRouter
from finam_core.storage.virtual_signal_trade_repository import VirtualSignalTradeRepository


class SignalTradeRuntime:
    """
    Русский комментарий:
    Runtime для Telegram-сигналов без real execution.

    Цепочка:
    1) register_signal() — отправили сигнал и открыли виртуальную сделку;
    2) on_quote() — проверили цену на SL/TP;
    3) при закрытии — отправили итог сделки с P&L;
    4) send_daily_summary() — отправили итог дня.
    """

    def __init__(self, signal_notifier: Any, outcome_notifier: Any | None = None) -> None:
        self.signal_notifier = signal_notifier
        self.outcome_notifier = outcome_notifier or signal_notifier
        self.notification_router = NotificationRouter()
        self.tracker = SignalPaperTradeTracker()
        self.reporter = TradeOutcomeReporter(self.outcome_notifier)
        # Русский комментарий: PostgreSQL-хранилище открытых виртуальных сделок для ручного закрытия.
        self.trade_repo = VirtualSignalTradeRepository()

    def register_signal(
        self,
        *,
        symbol: str,
        side: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        qty: float = 1.0,
        confidence: float = 0.0,
        regime: str = "unknown",
        reason: str = "",
    ) -> dict:
        """Русский комментарий: отправляет сигнал и открывает виртуальную сделку."""
        sent = False

        if hasattr(self.signal_notifier, "send_signal"):
            sent = bool(
                self.signal_notifier.send_signal(
                    symbol=symbol,
                    side=side,
                    entry=float(entry),
                    stop_loss=float(stop_loss),
                    take_profit=float(take_profit),
                    confidence=float(confidence or 0.0),
                    regime=regime,
                    reason=reason,
                )
            )

        trade = self.tracker.open_trade(
            symbol=symbol,
            side=side,
            entry=float(entry),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            qty=float(qty),
        )

        repo_trade_id = None
        try:
            repo_trade_id = self.trade_repo.open_trade(
                symbol=symbol,
                side=side,
                qty=float(qty),
                entry_price=float(entry),
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
                raw_json={
                    "confidence": confidence,
                    "regime": regime,
                    "reason": reason,
                    "telegram_sent": sent,
                },
            )
            print(
                f"VIRTUAL_SIGNAL_TRADE_OPENED id={repo_trade_id} symbol={symbol} side={side} "
                f"entry={entry} stop={stop_loss} take={take_profit}",
                flush=True,
            )
        except Exception as exc:
            print(f"VIRTUAL_SIGNAL_TRADE_REPO_OPEN_FAILED symbol={symbol} error={exc}", flush=True)

        return {
            "status": "OPENED",
            "telegram_sent": sent,
            "repo_trade_id": repo_trade_id,
            "trade": asdict(trade),
        }

    def on_quote(self, *, symbol: str, price: float) -> list[dict]:
        """Русский комментарий: обновляет виртуальные сделки по цене и отправляет итог закрытых сделок."""
        closed = self.tracker.on_price(symbol, float(price))
        results = []

        for trade in closed:
            outcome = self.reporter.analyze(
                symbol=trade.symbol,
                side=trade.side,
                entry_price=trade.entry,
                exit_price=float(trade.exit_price or price),
                qty=trade.qty,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                reason=f"virtual_trade_closed:{trade.close_reason}",
            )

            sent = self.notification_router.send(
                trigger="trade_outcome",
                text=(
                    "📊 ИТОГ СДЕЛКИ\n\n"
                    f"Инструмент: {outcome.symbol}\n"
                    f"Сторона: {outcome.side}\n"
                    f"Вход: {outcome.entry_price:.4f}\n"
                    f"Выход: {outcome.exit_price:.4f}\n"
                    f"P&L: {outcome.pnl:.4f}\n"
                    f"P&L %: {outcome.pnl_pct:.2f}%\n"
                    f"Факт R: {outcome.r_multiple:.2f}R\n"
                    f"Результат: {outcome.result}\n"
                    f"Причина: {outcome.reason}"
                ),
            )

            results.append(
                {
                    "symbol": trade.symbol,
                    "status": trade.status,
                    "close_reason": trade.close_reason,
                    "pnl": trade.pnl,
                    "r_multiple": trade.r_multiple,
                    "telegram_sent": sent,
                    "outcome": asdict(outcome),
                }
            )

        return results

    def build_daily_summary_text(self) -> str:
        """Русский комментарий: формирует текст дневного отчёта по виртуальным сделкам."""
        summary = self.tracker.daily_summary()

        text = (
            "📌 ИТОГ ДНЯ ПО СИГНАЛАМ\n\n"
            f"Всего сигналов: {summary['total']}\n"
            f"Закрыто сделок: {summary['closed']}\n"
            f"Открыто сделок: {summary['open']}\n"
            f"Профитных: {summary['wins']}\n"
            f"Убыточных: {summary['losses']}\n\n"
            f"Итоговый P&L: {summary['pnl']:.4f}\n"
            f"Средний R: {summary['avg_r']:.2f}R\n\n"
            "Режим: виртуальное сопровождение сигналов, реальные заявки не отправлялись."
        )

        return text

    def send_daily_summary(self) -> bool:
        """Русский комментарий: отправляет итог дня в Telegram."""
        text = self.build_daily_summary_text()

        return bool(self.notification_router.send(trigger="pnl_report", text=text))
