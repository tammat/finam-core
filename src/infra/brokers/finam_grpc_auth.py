import grpc


class JwtAuthInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, token: str):
        self._token = token

    def intercept_unary_unary(self, continuation, client_call_details, request):
        metadata = []

        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)

        metadata.append(("authorization", f"Bearer {self._token}"))

        new_details = grpc.ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
            client_call_details.compression,
        )

        return continuation(new_details, request)
