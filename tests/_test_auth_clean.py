import os
import grpc

from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2
from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2_grpc

def main():
    secret = os.getenv("FINAM_API_SECRET")
    if not secret:
        raise SystemExit("FINAM_API_SECRET is empty")

    channel = grpc.secure_channel(
        "tradeapi.finam.ru:443",
        grpc.ssl_channel_credentials()
    )

    stub = auth_service_pb2_grpc.AuthServiceStub(channel)

    resp = stub.Auth(
        auth_service_pb2.AuthRequest(secret=secret)
    )

    print("JWT:", resp.token)

if __name__ == "__main__":
    main()