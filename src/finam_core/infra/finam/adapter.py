from finam_core.infra.finam.client import FinamClient
from finam_proto.grpc.tradeapi.v1.accounts.accounts_service_pb2 import GetAccountRequest
from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2


class FinamAdapter:
    def __init__(self, token: str):
        self.client = FinamClient()

    def get_account(self, account_id: str):
        request = GetAccountRequest(account_id=account_id)
        return self.client.get_account(request)

    def place_order(
        self,
        account_id: str,
        symbol: str,
        quantity: float,
        side: int,
        price: float | None = None,
    ):
        request = orders_service_pb2.PlaceOrderRequest(
            account_id=account_id,
            symbol=symbol,
            quantity=str(quantity),
            side=side,
            price=str(price) if price else None,
        )
        return self.client.place_order(request)

    def close(self):
        self.client.stop()