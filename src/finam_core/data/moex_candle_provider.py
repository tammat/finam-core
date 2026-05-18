from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import requests


@dataclass(frozen=True)
class MoexCandle:
    symbol: str
    begin: str
    end: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MoexCandleProvider:
    """Русский комментарий: внешний поставщик свечей MOEX ISS без обязательного хранения bars."""

    INTERVALS = {
        "M1": 1,
        "M5": 5,
        "M10": 10,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "D1": 24,
    }

    def __init__(self, *, timeout_sec: float = 20.0) -> None:
        self.timeout_sec = timeout_sec

    def load_candles(
        self,
        *,
        symbol: str,
        board: str,
        engine: str,
        market: str,
        timeframe: str,
        date_from: str,
        date_to: str,
        limit: int = 500,
    ) -> list[MoexCandle]:
        interval = self.INTERVALS.get(timeframe.upper())
        if interval is None:
            raise ValueError(f"Неподдерживаемый timeframe: {timeframe}")

        url = (
            "https://iss.moex.com/iss/engines/"
            f"{engine}/markets/{market}/boards/{board}/securities/{symbol}/candles.json"
        )

        params = {
            "from": date_from,
            "till": date_to,
            "interval": interval,
            "start": 0,
        }

        candles: list[MoexCandle] = []

        while True:
            response = requests.get(url, params=params, timeout=self.timeout_sec)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            block = data.get("candles") or {}
            columns = block.get("columns") or []
            rows = block.get("data") or []

            if not rows:
                break

            idx = {name: i for i, name in enumerate(columns)}

            for row in rows:
                candles.append(
                    MoexCandle(
                        symbol=symbol,
                        begin=str(row[idx["begin"]]),
                        end=str(row[idx["end"]]),
                        open=float(row[idx["open"]]),
                        high=float(row[idx["high"]]),
                        low=float(row[idx["low"]]),
                        close=float(row[idx["close"]]),
                        volume=float(row[idx.get("volume", idx.get("value", 0))] or 0.0),
                    )
                )

            if len(rows) < limit:
                break

            params["start"] = int(params["start"]) + len(rows)

        return candles
