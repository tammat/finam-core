from google.type import decimal_pb2
from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2
from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2_grpc
from finam_proto.grpc.tradeapi.v1 import side_pb2


class FinamOrdersClient:

    def __init__(self, channel, token):
        self.stub = orders_service_pb2_grpc.OrdersServiceStub(channel)
        self.token = token

    def place_market_order(self, symbol, side, qty, account):

        metadata = [("authorization", f"Bearer {self.token}")]

        quantity = decimal_pb2.Decimal(value=str(int(qty)))

        req = orders_service_pb2.Order(
            account_id=str(account),
            symbol=str(symbol),
            quantity=quantity,
            side=side_pb2.SIDE_BUY if side == "BUY" else side_pb2.SIDE_SELL,
            type=orders_service_pb2.ORDER_TYPE_MARKET,
            time_in_force=orders_service_pb2.TIME_IN_FORCE_DAY
        )

        print("ORDER REQUEST:", req)

        return self.stub.PlaceOrder(req, metadata=metadata)