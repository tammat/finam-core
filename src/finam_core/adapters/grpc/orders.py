import grpc
import secrets

from google.type import decimal_pb2

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2
from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2_grpc
from finam_proto.grpc.tradeapi.v1 import side_pb2

def _dec_qty(qty: int | float) -> decimal_pb2.Decimal:
    # В твоём аккаунте quantity в позициях идёт "150.0", "15.0", "8.0" → делаем так же
    q = float(qty)
    return decimal_pb2.Decimal(value=f"{q:.1f}")

def _dec_price(price: float) -> decimal_pb2.Decimal:
    # цена лучше с 2 знаками, но можно и больше — Finam примет строку
    return decimal_pb2.Decimal(value=f"{float(price):.2f}")
class FinamOrdersClient:
    def __init__(self, host: str = "api.finam.ru:443"):
        self.host = host
        self.token_manager = FinamTokenManager()
        self.channel = grpc.secure_channel(self.host, grpc.ssl_channel_credentials())
        self.stub = orders_service_pb2_grpc.OrdersServiceStub(self.channel)

    def place_market_order(self, symbol: str, side: str, qty: int, account: str):
        token = self.token_manager.get_token()
        md = [("authorization", f"Bearer {token}")]

        req = orders_service_pb2.Order(
            account_id=str(account),
            symbol=str(symbol),
            quantity=_dec_qty(qty),
            side=side_pb2.SIDE_BUY if side == "BUY" else side_pb2.SIDE_SELL,
            type=orders_service_pb2.ORDER_TYPE_MARKET,
            time_in_force=orders_service_pb2.TIME_IN_FORCE_DAY,
        )
        print("ORDER REQUEST:", req)
        return self.stub.PlaceOrder(req, metadata=md)

    def build_limit_order(self, symbol: str, side: str, qty: int, limit_price: float, account: str):
        return orders_service_pb2.Order(
            account_id=str(account),
            symbol=str(symbol),
            quantity=_dec_qty(qty),
            side=side_pb2.SIDE_BUY if side == "BUY" else side_pb2.SIDE_SELL,
            type=orders_service_pb2.ORDER_TYPE_LIMIT,
            limit_price=_dec_price(limit_price),
            time_in_force=orders_service_pb2.TIME_IN_FORCE_DAY,
            valid_before=orders_service_pb2.VALID_BEFORE_END_OF_DAY,
            client_order_id=secrets.token_hex(8),
        )

    def place_limit_order(self, symbol: str, side: str, qty: int, limit_price: float, account: str):
        req = self.build_limit_order(symbol, side, qty, limit_price, account)
        print("ORDER REQUEST:", req)
        return self.stub.PlaceOrder(req, metadata=self._md())

    def _md(self):
        jwt = self.token_manager.get_token()
        return [("authorization", f"Bearer {jwt}")]