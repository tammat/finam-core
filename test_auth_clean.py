import os
import grpc
from dotenv import load_dotenv

from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2
from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2_grpc

load_dotenv()

def main():
    secret = os.getenv("FINAM_API_SECRET")

    channel = grpc.secure_channel(
        "api.finam.ru:443",
        grpc.ssl_channel_credentials()
    )

    stub = auth_service_pb2_grpc.AuthServiceStub(channel)

    response = stub.Auth(
        auth_service_pb2.AuthRequest(secret=secret)
    )

    print("JWT:", response.token)

if __name__ == "__main__":
    main()