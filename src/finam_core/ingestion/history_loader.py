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
        bars = self.client.get_bars(symbol=symbol, timeframe=timeframe, start=start, end=end)

        out: List[Dict[str, Any]] = []
        for b in bars:
            # Русский коммент: поля зависят от proto; ниже “best effort”
            ts = getattr(b, "timestamp", None) or getattr(b, "time", None)
            close = getattr(getattr(b, "close", None), "value", None) if getattr(b, "close", None) else getattr(b, "close", None)
            vol = getattr(getattr(b, "volume", None), "value", None) if getattr(b, "volume", None) else getattr(b, "volume", None)

            out.append(
                {
                    "ts": ts,
                    "close": float(close) if close is not None else None,
                    "volume": float(vol) if vol is not None else None,
                    "raw": b,
                }
            )

        return out