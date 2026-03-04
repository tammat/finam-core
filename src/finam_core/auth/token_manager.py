import time
import grpc
import os

from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2
from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2_grpc


class FinamTokenManager:

    def __init__(self):

        self.secret = os.getenv("FINAM_SECRET")
        self.host = "api.finam.ru:443"

        self.token = None
        self.expire_ts = 0

        creds = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(self.host, creds)

        self.stub = auth_service_pb2_grpc.AuthServiceStub(channel)

    def get_token(self):

        if time.time() > self.expire_ts:
            self._refresh()

        return self.token

    def _refresh(self):

        req = auth_service_pb2.AuthRequest(secret=self.secret)

        resp = self.stub.Auth(req)

        self.token = resp.access_token
        self.expire_ts = time.time() + resp.expires_in - 5