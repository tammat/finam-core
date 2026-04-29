# -*- coding: utf-8 -*-
"""
Показ текущего счёта Finam через gRPC AccountsService.GetAccount.
"""

from __future__ import annotations

import os
import grpc
from google.protobuf.json_format import MessageToDict

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2_grpc


def main() -> None:
    account_id = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("FINAM_ACCOUNT_ID/ACCOUNT_ID is required")

    host = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")

    tm = FinamTokenManager()
    jwt = tm.get_token()

    channel = grpc.secure_channel(host, grpc.ssl_channel_credentials())
    stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

    req = accounts_service_pb2.GetAccountRequest(account_id=account_id)
    resp = stub.GetAccount(req, metadata=[("authorization", f"Bearer {jwt}")], timeout=20)

    data = MessageToDict(resp, preserving_proto_field_name=True)

    print("ACCOUNT_ID:", account_id)
    print("RAW:")
    print(data)


if __name__ == "__main__":
    main()
