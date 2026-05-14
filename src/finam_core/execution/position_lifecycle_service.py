from __future__ import annotations

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

    На первом этапе сервис является тонкой обёрткой над существующими
    методами PaperTradingPipeline. Это снижает риск регрессии:
    поведение не меняем, только готовим вынос логики из paper_pipeline.py.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def on_position_quote(self, data: PositionLifecycleInput) -> None:
        p = self.pipeline

        # Русский комментарий: порядок вызовов сохраняем как в текущем pipeline.
        p._evaluate_take_profit_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        p._evaluate_partial_close_engine(
            symbol=data.symbol,
            qty=abs(float(data.qty)),
            price=float(data.price),
            avg_price=float(data.avg_price),
            stop_price=None,
        )

        p._evaluate_profit_lock_engine(
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
