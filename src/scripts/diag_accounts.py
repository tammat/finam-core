import grpc
from finam_core.auth.token_manager import FinamTokenManager

from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2 as acc_pb2
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2_grpc as acc_grpc

HOST = "api.finam.ru:443"

def main():
    tm = FinamTokenManager()
    jwt = tm.get_token()
    md = [("authorization", f"Bearer {jwt}")]

    ch = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())
    stub = acc_grpc.AccountsServiceStub(ch)

    # Обычно у Finam: GetAccounts(google.protobuf.Empty) или AccountsRequest.
    # Попробуем оба варианта аккуратно.
    try:
        from google.protobuf import empty_pb2
        resp = stub.GetAccounts(empty_pb2.Empty(), metadata=md)
    except Exception:
        resp = stub.GetAccounts(acc_pb2.GetAccountsRequest(), metadata=md)

    print(resp)

if __name__ == "__main__":
    main()
