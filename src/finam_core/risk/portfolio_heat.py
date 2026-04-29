# src/finam_core/risk/portfolio_heat.py

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PortfolioHeatDecision:
    allowed: bool
    reason: str
    current_heat: float
    projected_heat: float
    limit: float


class PortfolioHeatEngine:
    """
    Русский коммент: Portfolio Heat Layer.
    Контролирует суммарную нагрузку портфеля до входа.
    Не отправляет заявки напрямую.
    """

    def __init__(self):
        self.heat_limit = float(os.getenv("PORTFOLIO_HEAT_LIMIT", "0.80"))

    def evaluate(self, portfolio_value: float, current_exposure: float, new_trade_value: float) -> PortfolioHeatDecision:
        pv = float(portfolio_value or 0.0)
        exposure = abs(float(current_exposure or 0.0))
        trade_value = abs(float(new_trade_value or 0.0))

        if pv <= 0:
            return PortfolioHeatDecision(False, "invalid_portfolio_value", 0.0, 0.0, self.heat_limit)

        current_heat = exposure / pv
        projected_heat = (exposure + trade_value) / pv

        if projected_heat > self.heat_limit:
            return PortfolioHeatDecision(False, "portfolio_heat_exceeded", current_heat, projected_heat, self.heat_limit)

        return PortfolioHeatDecision(True, "ok", current_heat, projected_heat, self.heat_limit)
