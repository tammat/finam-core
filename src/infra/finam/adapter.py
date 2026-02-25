from finam_grpc_client import FinamClient
from finam_grpc_client.proto.grpc.tradeapi.v1.accounts.accounts_service_pb2 import GetAccountRequest
from finam_grpc_client.proto.grpc.tradeapi.v1.orders.orders_service_pb2 import PlaceOrderRequest


class FinamAdapter:
    def __init__(self, token: str):
        self.client = FinamClient(secret=token)
        self.client.start()

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
        request = PlaceOrderRequest(
            account_id=account_id,
            symbol=symbol,
            quantity=str(quantity),
            side=side,
            price=str(price) if price else None,
        )
        return self.client.place_order(request)

    def close(self):
        self.client.stop()