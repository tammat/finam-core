import os
import grpc

from finam_proto.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2,
    accounts_service_pb2_grpc,
)

FINAM_TOKEN = os.getenv("FINAM_TOKEN")

def main():
    if not FINAM_TOKEN:
        raise RuntimeError("FINAM_TOKEN not set")

    channel = grpc.secure_channel(
        "tradeapi.finam.ru:443",
        grpc.ssl_channel_credentials()
    )

    stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

    metadata = [
        ("authorization", f"Bearer {FINAM_TOKEN}")
    ]

    response = stub.GetAccounts(
        accounts_service_pb2.GetAccountsRequest(),
        metadata=metadata
    )

    print("ACCOUNTS RESPONSE:")
    print(response)


if __name__ == "__main__":
    main()