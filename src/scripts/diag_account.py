import grpc

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2 as acc_pb2
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2_grpc as acc_grpc

HOST = "api.finam.ru:443"
ACCOUNT_ID = "1943312"

def main():
    tm = FinamTokenManager()
    jwt = tm.get_token()
    md = [("authorization", f"Bearer {jwt}")]

    ch = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())
    stub = acc_grpc.AccountsServiceStub(ch)

    # почти всегда так:
    if hasattr(acc_pb2, "GetAccountRequest"):
        req = acc_pb2.GetAccountRequest(account_id=ACCOUNT_ID)
    else:
        # fallback: если имя другое — упадет, но покажет что искать
        req = acc_pb2.GetAccount(account_id=ACCOUNT_ID)  # type: ignore

    resp = stub.GetAccount(req, metadata=md)
    print(resp)

if __name__ == "__main__":
    main()
