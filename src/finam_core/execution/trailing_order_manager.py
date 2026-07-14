# -*- coding: utf-8 -*-
"""
TrailingOrderManager — robot-side trailing stop manager.
Русский комментарий: модуль только рассчитывает действие по защитной stop-заявке.
Заявки брокеру не отправляет.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrailingOrderDecision:
    action: str
    symbol: str
    side: str
    qty: float
    stop_price: float | None
    reason: str


class TrailingOrderManager:
    def __init__(self, policy: dict) -> None:
        self.policy = policy

    @classmethod
    def from_versioned_policy(cls) -> "TrailingOrderManager":
        default_path = Path(__file__).resolve().parents[3] / "config/runtime/trailing_order_policy_v1.json"
        policy_path = Path(os.getenv("TRAILING_ORDER_POLICY_PATH", str(default_path)))
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if not policy.get("catalog_version") or not isinstance(policy.get("instrument_policies"), dict):
            raise ValueError("INVALID_TRAILING_ORDER_POLICY")
        return cls(policy)

    def _parameters(self, symbol: str) -> tuple[float, float, int] | None:
        root = str(symbol).split("@", 1)[0][:2]
        item = self.policy["instrument_policies"].get(root)
        if not item or not item.get("enabled", False):
            return None
        return float(item["trail_abs"]), float(item["min_replace_step"]), int(item["price_precision"])

    def evaluate_long(
        self,
        *,
        symbol: str,
        qty: float,
        last_price: float,
        current_stop: float | None = None,
    ) -> TrailingOrderDecision:
        qty = float(qty or 0.0)
        last = float(last_price)

        parameters = self._parameters(symbol)
        if parameters is None:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, current_stop, "policy_not_configured")
        trail_abs, min_replace_step, price_precision = parameters

        if qty <= 0:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, current_stop, "no_long_position")

        new_stop = round(last - trail_abs, price_precision)

        if current_stop is None:
            return TrailingOrderDecision("PLACE_STOP", symbol, "SELL", qty, new_stop, "initial_trailing_stop")

        old_stop = float(current_stop)

        if new_stop <= old_stop:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, old_stop, "stop_not_improved")

        if new_stop - old_stop < min_replace_step:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, old_stop, "replace_step_too_small")

        return TrailingOrderDecision("REPLACE_STOP", symbol, "SELL", qty, new_stop, "trailing_stop_improved")
