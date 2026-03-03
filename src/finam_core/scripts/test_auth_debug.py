import os
import grpc

from finam_proto.grpc.tradeapi.v1.auth import (
    auth_service_pb2,
    auth_service_pb2_grpc,
)

def main():
    api_secret = os.getenv("FINAM_API_SECRET")
    print("SECRET EXISTS:", bool(api_secret))

    channel = grpc.secure_channel(
        "tradeapi.finam.ru:443",
        grpc.ssl_channel_credentials(),
    )

    print("CHANNEL CREATED")

    stub = auth_service_pb2_grpc.AuthServiceStub(channel)
    print("STUB CREATED")

    try:
        response = stub.Auth(
            auth_service_pb2.AuthRequest(secret=api_secret),
            metadata=(("x-api-key", api_secret),),
            timeout=10,
        )
        print("AUTH RESPONSE RECEIVED")
        print(response)

    except grpc.RpcError as e:
        print("RPC ERROR")
        print("code:", e.code())
        print("details:", e.details())
        print("debug:", e.debug_error_string())

if __name__ == "__main__":
    main()