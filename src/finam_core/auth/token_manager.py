# -*- coding: utf-8 -*-
"""
FinamTokenManager
- получает JWT через gRPC AuthService.Auth(secret)
- кэширует токен на ttl_sec
- устойчив к временным сетевым ошибкам: timeout + retry + пересоздание channel

ENV:
- FINAM_SECRET (обязательно)
- FINAM_API_HOST (опционально, default api.finam.ru:443)
- FINAM_AUTH_TIMEOUT_SEC (default 10)
- FINAM_TOKEN_TTL_SEC (default 600)
- FINAM_AUTH_RETRIES (default 3)
- FINAM_GRPC_KEEPALIVE_TIME_MS (default 30000)
- FINAM_GRPC_KEEPALIVE_TIMEOUT_MS (default 10000)
"""

from __future__ import annotations

import os
import time
import threading
import grpc

from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2 as auth_pb2
from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2_grpc as auth_grpc


class FinamTokenManager:
    def __init__(self, host: str | None = None, secret: str | None = None):
        self.secret = (secret or os.getenv("FINAM_SECRET") or "").strip()
        if not self.secret:
            raise RuntimeError("FINAM_SECRET is required for FinamTokenManager")

        self.host = (host or os.getenv("FINAM_API_HOST") or "api.finam.ru:443").strip()

        self.ttl_sec = int(os.getenv("FINAM_TOKEN_TTL_SEC", "600"))
        self.timeout_sec = float(os.getenv("FINAM_AUTH_TIMEOUT_SEC", "10"))
        self.retries = int(os.getenv("FINAM_AUTH_RETRIES", "3"))

        self.token: str | None = None
        self.expire_ts: float = 0.0

        self._lock = threading.Lock()

        self.channel = None
        self.stub = None
        self._connect()

    def _connect(self) -> None:
        # keepalive как в MarketData — чтобы 24/7 соединение не “умирало” в idle
        ka_time_ms = int(os.getenv("FINAM_GRPC_KEEPALIVE_TIME_MS", "30000"))
        ka_timeout_ms = int(os.getenv("FINAM_GRPC_KEEPALIVE_TIMEOUT_MS", "10000"))
        opts = [
            ("grpc.keepalive_time_ms", ka_time_ms),
            ("grpc.keepalive_timeout_ms", ka_timeout_ms),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.min_time_between_pings_ms", ka_time_ms),
            ("grpc.http2.min_ping_interval_without_data_ms", ka_time_ms),
        ]

        creds = grpc.ssl_channel_credentials()
        self.channel = grpc.secure_channel(self.host, creds, options=opts)
        self.stub = auth_grpc.AuthServiceStub(self.channel)

    def close(self) -> None:
        try:
            if self.channel is not None:
                self.channel.close()
        except Exception:
            pass

    def get_token(self) -> str:
        now = time.time()
        if now < self.expire_ts and self.token:
            return self.token

        with self._lock:
            now = time.time()
            if now < self.expire_ts and self.token:
                return self.token
            self._refresh_locked()
            return self.token  # type: ignore[return-value]

    def _refresh_locked(self) -> None:
        last_err = None
        for attempt in range(1, self.retries + 1):
            try:
                req = auth_pb2.AuthRequest(secret=self.secret)
                # timeout — чтобы не “висеть”
                resp = self.stub.Auth(req, timeout=self.timeout_sec)
                self.token = resp.token
                # небольшой safety-margin (чтобы не словить истечение ровно на границе)
                self.expire_ts = time.time() + max(30, self.ttl_sec - 15)
                return
            except grpc.RpcError as e:
                last_err = e
                # пересоздаём канал (часто помогает после UNAVAILABLE/Socket closed)
                try:
                    self.close()
                except Exception:
                    pass
                self._connect()
                time.sleep(min(0.5 * attempt, 2.0))
            except Exception as e:
                last_err = e
                time.sleep(min(0.5 * attempt, 2.0))

        raise RuntimeError(f"FinamTokenManager Auth failed after {self.retries} retries: {last_err}")
