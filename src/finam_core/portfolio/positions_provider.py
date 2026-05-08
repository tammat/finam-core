from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    qty: float
    avg_price: float | None = None
    raw: Any | None = None


class PositionsProvider:
    def __init__(self, client):
        self.client = client

    def get_positions(self) -> list[BrokerPosition]:
        data = self.client.get_portfolios()

        positions = []

        # Поддерживаем dict и protobuf/list-like форматы.
        raw_positions = []

        if isinstance(data, dict):
            raw_positions = (
                data.get("positions")
                or data.get("securities")
                or data.get("portfolio", {}).get("positions")
                or []
            )
        else:
            raw_positions = (
                getattr(data, "positions", None)
                or getattr(data, "securities", None)
                or []
            )

        for p in raw_positions:
            symbol = self._get(p, "symbol") or self._get(p, "ticker")
            qty = self._to_float(
                self._get(p, "qty")
                or self._get(p, "quantity")
                or self._get(p, "balance")
                or self._get(p, "lots")
                or 0
            )

            if not symbol or qty == 0:
                continue

            avg_price = self._to_float(
                self._get(p, "avg_price")
                or self._get(p, "average_price")
                or self._get(p, "price")
            )

            positions.append(
                BrokerPosition(
                    symbol=str(symbol),
                    qty=qty,
                    avg_price=avg_price,
                    raw=p,
                )
            )

        return positions

    @staticmethod
    def _get(obj, name: str):
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    @staticmethod
    def _to_float(v):
        if v is None:
            return None
        try:
            if hasattr(v, "value"):
                return float(v.value)
            return float(v)
        except Exception:
            return None
