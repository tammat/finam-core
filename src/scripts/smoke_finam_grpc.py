import os
import grpc

from finam_proto.grpc.tradeapi.v1.assets import assets_service_pb2 as a_pb2
from finam_proto.grpc.tradeapi.v1.assets import assets_service_pb2_grpc as a_grpc

HOST = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")

def main() -> int:
    token = os.getenv("FINAM_TOKEN")
    if not token:
        print("ENV ERROR: FINAM_TOKEN is not set")
        return 2

    channel = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())
    stub = a_grpc.AssetsServiceStub(channel)

    md = (("authorization", f"Bearer {token}"),)

    try:
        resp = stub.AllAssets(a_pb2.AllAssetsRequest(), metadata=md, timeout=15)
        assets = getattr(resp, "assets", [])
        print(f"OK: AllAssets -> {len(assets)} assets")
        for a in assets[:10]:
            print(getattr(a, "symbol", ""))
        return 0
    except grpc.RpcError as e:
        print(f"gRPC ERROR: {e.code().name} | {e.details()}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
