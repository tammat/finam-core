# -*- coding: utf-8 -*-
"""
HistoryLoader: загружает свечи через FinamBarsClient и нормализует в list[dict].
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any

from finam_core.ingestion.bars_client import FinamBarsClient


class HistoryLoader:
    def __init__(self, host: str = "api.finam.ru:443"):
        self.client = FinamBarsClient(host=host)

    def close(self) -> None:
        self.client.close()

    def load(self, symbol: str, timeframe, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        bars_resp = self.client.get_bars(symbol=symbol, timeframe=timeframe, start=start, end=end)

        # Русский коммент: Finam gRPC Bars обычно возвращает unary BarsResponse, где бары лежат в поле `.bars`.
        # Но на всякий случай поддерживаем и вариант, когда get_bars() вернёт уже iterable/stream.
        bars_iter = getattr(bars_resp, "bars", None)
        if bars_iter is None:
            bars_iter = bars_resp

        out: List[Dict[str, Any]] = []
        for b in bars_iter:
            # Русский коммент: timestamp обычно protobuf Timestamp; нормализуем в ISO UTC строку.
            ts_pb = getattr(b, "timestamp", None) or getattr(b, "time", None)
            ts_iso = None
            if ts_pb is not None:
                try:
                    # google.protobuf.timestamp_pb2.Timestamp имеет ToDatetime()
                    dt = ts_pb.ToDatetime()
                    # нормализуем в UTC и сериализуем
                    if getattr(dt, "tzinfo", None) is None:
                        ts_iso = dt.isoformat() + "+00:00"
                    else:
                        ts_iso = dt.astimezone(__import__("datetime").timezone.utc).isoformat()
                except Exception:
                    try:
                        # fallback: если это уже datetime
                        ts_iso = ts_pb.isoformat()
                    except Exception:
                        ts_iso = str(ts_pb)

            def _dec(x):
                # Русский коммент: Decimal в proto часто хранится как объект с .value (строка)
                if x is None:
                    return None
                try:
                    v = getattr(x, "value", None)
                    return float(v) if v is not None else float(x)
                except Exception:
                    return None

            o = _dec(getattr(b, "open", None))
            h = _dec(getattr(b, "high", None))
            l = _dec(getattr(b, "low", None))
            c = _dec(getattr(b, "close", None))
            v = _dec(getattr(b, "volume", None))

            out.append(
                {
                    "ts": ts_iso,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": v,
                    "raw": b,
                }
            )

        return out