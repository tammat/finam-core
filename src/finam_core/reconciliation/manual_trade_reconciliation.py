# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrokerPositionSnapshot:
    symbol: str
    qty: float
    average_price: float | None = None
    current_price: float | None = None
    unrealized_pnl: float | None = None


class ManualTradeReconciliation:
    """
    Read-only reconciliation layer.

    Назначение:
    - читать реальные позиции брокера;
    - не выставлять заявки;
    - сравнивать ручной вход с локальными сигналами;
    - готовить сопровождение позиции.
    """

    def __init__(self, broker_client: Any):
        self.broker_client = broker_client

    def get_broker_positions(self) -> list[BrokerPositionSnapshot]:
        raw_positions = self.broker_client.get_positions()

        result: list[BrokerPositionSnapshot] = []

        for p in raw_positions or []:
            result.append(
                BrokerPositionSnapshot(
                    symbol=str(self._get(p, "symbol", "")),
                    qty=float(self._get(p, "qty", 0.0) or 0.0),
                    average_price=self._to_float(
                        self._get(p, "average_price")
                        or self._get(p, "avg_price")
                        or self._get(p, "balance_price")
                    ),
                    current_price=self._to_float(self._get(p, "current_price")),
                    unrealized_pnl=self._to_float(self._get(p, "unrealized_pnl")),
                )
            )

        return result

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None

        if isinstance(value, dict) and "value" in value:
            value = value["value"]

        try:
            return float(value)
        except Exception:
            return None
