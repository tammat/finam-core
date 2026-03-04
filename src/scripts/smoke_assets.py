import grpc

from finam_core.auth.token_manager import FinamTokenManager

from finam_proto.grpc.tradeapi.v1.assets import assets_service_pb2
from finam_proto.grpc.tradeapi.v1.assets import assets_service_pb2_grpc


def main():

    tm = FinamTokenManager()
    token = tm.get_token()

    channel = grpc.secure_channel(
        "api.finam.ru:443",
        grpc.ssl_channel_credentials()
    )

    stub = assets_service_pb2_grpc.AssetsServiceStub(channel)

    metadata = [
        ("authorization", f"Bearer {token}")
    ]

    req = assets_service_pb2.AssetsRequest()

    resp = stub.Assets(req, metadata=metadata)

    print("assets count:", len(resp.assets))


if __name__ == "__main__":
    main()