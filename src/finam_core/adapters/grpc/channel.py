import grpc
from finam_core.auth.token_manager import FinamTokenManager


class AuthInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
):

    def __init__(self, token_manager: FinamTokenManager):
        self.tm = token_manager

    def _inject(self, client_call_details):
        token = self.tm.get_token()

        metadata = []
        if client_call_details.metadata:
            metadata = list(client_call_details.metadata)

        metadata.append(("authorization", f"Bearer {token}"))

        return client_call_details._replace(metadata=metadata)

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return continuation(self._inject(client_call_details), request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return continuation(self._inject(client_call_details), request)


class GrpcChannelFactory:

    def __init__(self, host: str, token_manager: FinamTokenManager):
        self.host = host
        self.tm = token_manager

    def create(self):

        options = [
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", True),
        ]

        creds = grpc.ssl_channel_credentials()

        channel = grpc.secure_channel(self.host, creds, options)

        interceptor = AuthInterceptor(self.tm)

        return grpc.intercept_channel(channel, interceptor)