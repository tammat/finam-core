import os
import grpc

from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2, auth_service_pb2_grpc
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2, accounts_service_pb2_grpc

TOKEN = os.environ["FINAM_TOKEN"]


def metadata_callback(context, callback):
    callback((("authorization", f"Bearer {TOKEN}"),), None)

auth_credentials = grpc.metadata_call_credentials(metadata_callback)
creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    auth_credentials
)

channel = grpc.secure_channel("tradeapi.finam.ru:443", creds)

stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

response = stub.GetAccounts(accounts_service_pb2.AccountsRequest())

print(response)