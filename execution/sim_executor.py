# execution/sim_executor.py

from uuid import uuid4

from domain.events import FillEvent
from execution.execution_engine import ExecutionEngine


class SimExecutionEngine(ExecutionEngine):
    def execute(self, order, market_price, ts):
        """
        SIM: частичное исполнение 50% + 50%
        Возвращает список FillEvent.
        """

        fills = []

        # Если уже полностью исполнен — ничего не делаем
        if getattr(order, "is_filled", False):
            return fills

        remaining = float(getattr(order, "remaining_qty", getattr(order, "qty", 0.0)))
        if remaining <= 0:
            return fills

        half_qty = remaining / 2.0

        for qty in (half_qty, remaining - half_qty):
            qty = float(qty)
            if qty <= 0:
                continue

            fill = FillEvent(
                fill_id=str(uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                qty=qty,
                price=float(market_price),
                commission=0.0,
                timestamp=ts,
            )

            # КРИТИЧНО: фиксируем исполнение в ордере (если модель поддерживает)
            if hasattr(order, "add_fill"):
                order.add_fill(fill)

            fills.append(fill)

        return fills