from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class FinamFuturesCandlesProvider:
    """
    Русский комментарий:
    Получение свечей MOEX ISS для срочного рынка FORTS.
    v1 использует board RFUD и явный диапазон дат from/till.
    """

    ISS_URL = "https://iss.moex.com/iss/engines/futures/markets/forts/securities"

    def load_candles(
        self,
        *,
        symbol: str,
        interval: int = 5,
        limit: int = 120,
        days_back: int = 10,
    ) -> list[dict[str, Any]]:
        secid = symbol.split("@")[0]

        till = datetime.now(timezone.utc).date()
        date_from = till - timedelta(days=days_back)

        url = f"{self.ISS_URL}/{secid}/candles.json"

        r = requests.get(
            url,
            params={
                "interval": interval,
                "from": date_from.isoformat(),
                "till": till.isoformat(),
                "start": 0,
            },
            timeout=20,
        )
        r.raise_for_status()

        payload = r.json()
        candles = payload.get("candles", {})
        columns = candles.get("columns", [])
        data = candles.get("data", [])

        result: list[dict[str, Any]] = []

        for row in data[-limit:]:
            item = dict(zip(columns, row))

            begin = item.get("begin")
            if not begin:
                continue

            ts = datetime.fromisoformat(begin).replace(tzinfo=timezone.utc)

            result.append(
                {
                    "ts": ts,
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(item.get("volume", 0) or item.get("value", 0) or 0),
                }
            )

        return result
