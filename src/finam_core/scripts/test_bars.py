import os
import grpc

from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2 as acc_pb2
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2_grpc as acc_grpc

token = os.environ["FINAM_TOKEN"]

channel = grpc.secure_channel(
    "api.finam.ru:443",
    grpc.ssl_channel_credentials()
)

stub = acc_grpc.AccountsServiceStub(channel)

resp = stub.GetAccounts(
    acc_pb2.GetAccountsRequest(),
    metadata=[("authorization", f"Bearer {token}")]
)

print(resp)