import os
import grpc

from finam_proto.grpc.tradeapi.v1.auth import (
    auth_service_pb2,
    auth_service_pb2_grpc,
)

def main():
    api_secret = os.getenv("FINAM_API_SECRET")
    if not api_secret:
        raise RuntimeError("FINAM_API_SECRET is empty")

    channel = grpc.secure_channel(
        "tradeapi.finam.ru:443",
        grpc.ssl_channel_credentials(),
    )

    stub = auth_service_pb2_grpc.AuthServiceStub(channel)

    # ВАЖНО: metadata передаем обязательно
    resp = stub.Auth(
        auth_service_pb2.AuthRequest(secret=api_secret),
        metadata=(("x-api-key", api_secret),),
        timeout=15,
    )

    # Обычно в ответе есть jwt
    print("AUTH OK")
    print(resp)

if __name__ == "__main__":
    main()