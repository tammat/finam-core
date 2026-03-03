import grpc
import requests
import os

from finam_proto.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2,
    accounts_service_pb2_grpc,
)


class FinamClient:
    def __init__(self, host, account_id, jwt="", secret=""):
        self.host = host
        self.account_id = account_id
        self.jwt = jwt
        self.secret = secret

        if not self.jwt:
            self.jwt = self._refresh_jwt()

        self._connect()

    def _refresh_jwt(self):
        if not self.secret:
            raise RuntimeError("FINAM_TOKEN not provided")

        r = requests.post(
            "https://api.finam.ru/v1/sessions",
            json={"secret": self.secret},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["token"]

    def _connect(self):
        creds = grpc.ssl_channel_credentials()
        self.channel = grpc.secure_channel(self.host, creds)
        self.accounts_stub = accounts_service_pb2_grpc.AccountsServiceStub(self.channel)

    def _metadata(self):
        return [("authorization", f"Bearer {self.jwt}")]

    def get_account(self):
        request = accounts_service_pb2.GetAccountRequest(
            account_id=self.account_id
        )
        return self.accounts_stub.GetAccount(
            request,
            metadata=self._metadata(),
        )