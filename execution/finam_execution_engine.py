from execution.execution_engine import BaseExecutionEngine
from infra.finam.adapter import FinamAdapter


class FinamExecutionEngine(BaseExecutionEngine):
    def __init__(self, token: str, account_id: str):
        self.account_id = account_id
        self.adapter = FinamAdapter(token)

    def execute(self, order):
        """
        order expected fields:
        - symbol
        - quantity
        - side ("BUY" | "SELL")
        - price (optional)
        """

        side_enum = 1 if order.side == "BUY" else 2

        response = self.adapter.place_order(
            account_id=self.account_id,
            symbol=order.symbol,
            quantity=order.quantity,
            side=side_enum,
            price=order.price,
        )

        return response

    def close(self):
        self.adapter.close()
