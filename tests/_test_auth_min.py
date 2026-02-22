import os
import grpc
from finam_proto.grpc.tradeapi.v1.auth import (
    auth_service_pb2,
    auth_service_pb2_grpc,
)

API_SECRET = os.getenv("FINAM_API_SECRET")

def main():
    channel = grpc.secure_channel(
        "tradeapi.finam.ru:443",
        grpc.ssl_channel_credentials(),
    )

    stub = auth_service_pb2_grpc.AuthServiceStub(channel)

    response = stub.Auth(
        auth_service_pb2.AuthRequest(secret=API_SECRET),
        metadata=(("x-api-key", API_SECRET),)
    )

    print(response)

if __name__ == "__main__":
    main()
