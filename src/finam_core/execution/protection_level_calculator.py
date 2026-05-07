# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ProtectionLevels:
    symbol: str
    entry_side: str
    exit_side: str
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    qty: int
    risk_per_unit: float
    reward_per_unit: float
    rr: float


class ProtectionLevelCalculator:
    """
    Русский комментарий:
    Профессиональная логика защиты:
    - риск задаётся в деньгах/процентах капитала;
    - stop-loss считается через ATR;
    - take-profit считается через risk/reward;
    - qty ограничивается допустимым риском.
    """

    def calculate(
        self,
        *,
        symbol: str,
        entry_side: str,
        entry_price: float,
        atr: float,
        equity: float,
        risk_pct: float = 0.005,
        stop_atr_mult: float = 2.0,
        reward_risk: float = 2.0,
        point_value: float = 1.0,
        max_qty: int = 1,
        tick_size: float = 0.01,
    ) -> ProtectionLevels:
        if entry_side not in ("BUY", "SELL"):
            raise ValueError("entry_side_must_be_BUY_or_SELL")
        if entry_price <= 0 or atr <= 0 or equity <= 0:
            raise ValueError("entry_price_atr_equity_must_be_positive")
        if risk_pct <= 0 or stop_atr_mult <= 0 or reward_risk <= 0:
            raise ValueError("risk_params_must_be_positive")

        risk_money = equity * risk_pct
        risk_per_unit = atr * stop_atr_mult * point_value

        raw_qty = math.floor(risk_money / risk_per_unit)
        qty = max(1, min(int(max_qty), int(raw_qty)))

        price_risk = atr * stop_atr_mult
        price_reward = price_risk * reward_risk

        if entry_side == "BUY":
            exit_side = "SELL"
            sl = entry_price - price_risk
            tp = entry_price + price_reward
        else:
            exit_side = "BUY"
            sl = entry_price + price_risk
            tp = entry_price - price_reward

        sl = self._round_to_tick(sl, tick_size)
        tp = self._round_to_tick(tp, tick_size)

        reward_per_unit = abs(tp - entry_price) * point_value
        rr = reward_per_unit / risk_per_unit if risk_per_unit else 0.0

        return ProtectionLevels(
            symbol=symbol,
            entry_side=entry_side,
            exit_side=exit_side,
            entry_price=entry_price,
            stop_loss_price=sl,
            take_profit_price=tp,
            qty=qty,
            risk_per_unit=risk_per_unit,
            reward_per_unit=reward_per_unit,
            rr=rr,
        )

    @staticmethod
    def _round_to_tick(value: float, tick_size: float) -> float:
        if tick_size <= 0:
            return value
        return round(round(value / tick_size) * tick_size, 10)
