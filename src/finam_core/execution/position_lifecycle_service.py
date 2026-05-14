from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionLifecycleInput:
    symbol: str
    qty: float
    price: float
    avg_price: float
    strategy: str = "default"


class PositionLifecycleService:
    """
    Русский комментарий:
    Единая точка входа для lifecycle сопровождения позиции.

    Этап 1:
    TakeProfitEngine перенесён внутрь сервиса.
    Остальные блоки пока вызываются через pipeline как fallback.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def _evaluate_take_profit_engine(
        self,
        *,
        symbol: str,
        qty: float,
        price: float,
        avg_price: float | None = None,
        stop_price: float | None = None,
    ) -> None:
        """Русский комментарий: dry-run take-profit расчёт без отправки заявок брокеру."""
        if os.getenv("ENABLE_TAKE_PROFIT_ENGINE", "0") != "1":
            return

        p = self.pipeline

        try:
            if qty <= 0 or price <= 0:
                return

            entry_price = float(avg_price or price)
            base_stop = float(
                stop_price
                or (
                    entry_price
                    * (1.0 - float(os.getenv("TAKE_PROFIT_DEFAULT_STOP_PCT", "0.01")))
                )
            )

            decision = p.take_profit_engine.evaluate_long(
                qty=float(qty),
                entry_price=entry_price,
                current_price=float(price),
                stop_price=base_stop,
            )

            if decision.action == "HOLD":
                return

            p._log_dedup(
                f"PIPE_TAKE_PROFIT_DECISION:{symbol}:{decision.action}:{decision.reason}",
                f"PIPE_TAKE_PROFIT_DECISION symbol={symbol} action={decision.action} "
                f"qty={qty} qty_to_close={decision.qty_to_close} "
                f"price={price} entry={entry_price} base_stop={base_stop} "
                f"take_price={decision.take_price} reason={decision.reason} dry_run=1",
                heartbeat_sec=300,
            )

            p.take_profit_event_repository.log_event(
                symbol=symbol,
                action=decision.action,
                qty=qty,
                qty_to_close=decision.qty_to_close,
                price=price,
                entry_price=entry_price,
                base_stop=base_stop,
                take_price=decision.take_price,
                reason=decision.reason,
                dry_run=True,
                raw={"source": "position_lifecycle_service", "engine": "TakeProfitEngine"},
            )

            p._save_position_lifecycle_state(
                symbol=symbol,
                entry_price=entry_price,
                initial_qty=qty,
                remaining_qty=max(0.0, float(qty) - float(decision.qty_to_close or 0.0)),
                current_take_profit=decision.take_price,
                source="take_profit_engine",
            )

        except Exception as exc:
            print(f"PIPE_TAKE_PROFIT_ERROR symbol={symbol} error={exc}", flush=True)

    def on_position_quote(self, data: PositionLifecycleInput) -> None:
        p = self.pipeline

        self._evaluate_take_profit_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        # Русский комментарий: partial close уже перенесён в сервис.
        self._evaluate_partial_close_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        # Русский комментарий: profit-lock уже перенесён в сервис.
        self._evaluate_profit_lock_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        p._evaluate_trailing_order_manager(
            data.symbol,
            abs(float(data.qty)),
            float(data.price),
        )
