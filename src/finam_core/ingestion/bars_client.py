# -*- coding: utf-8 -*-
"""
gRPC Bars client для исторических свечей Finam.

Русский коммент:
- JWT берём через FinamTokenManager (единственный источник JWT).
- Вызов делаем через MarketDataServiceStub (Bars).
"""

from __future__ import annotations

import grpc
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from google.protobuf.timestamp_pb2 import Timestamp

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc


class FinamBarsClient:
    def __init__(self, host: str = "api.finam.ru:443"):
        self.host = host
        self.tm = FinamTokenManager()
        self.channel = grpc.secure_channel(self.host, grpc.ssl_channel_credentials())
        self.stub = md_grpc.MarketDataServiceStub(self.channel)

    def close(self) -> None:
        try:
            self.channel.close()
        except Exception:
            pass

    def _md(self):
        jwt = self.tm.get_token()
        return [("authorization", f"Bearer {jwt}")]

    @staticmethod
    def _ts(dt: datetime) -> Timestamp:
        if dt.tzinfo is None:
            # Русский коммент: считаем, что вход в UTC, если tz не задан
            dt = dt.replace(tzinfo=timezone.utc)
        ts = Timestamp()
        ts.FromDatetime(dt)
        return ts

    def get_bars(
        self,
        symbol: str,
        timeframe,  # тип зависит от твоего proto; передаём как есть
        start: datetime,
        end: datetime,
    ):
        req = md_pb2.BarsRequest(
            symbol=symbol,
            timeframe=timeframe,
            interval=md_pb2.Interval(  # если Interval лежит в другом proto — поправим по месту
                start_time=self._ts(start),
                end_time=self._ts(end),
            ),
        )
        return self.stub.Bars(req, metadata=self._md())