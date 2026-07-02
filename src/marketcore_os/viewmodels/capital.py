from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CapitalViewModel:
    planned_capital: Decimal
    working_capital: Decimal
    available_capital: Decimal
    working_pct: Decimal
    available_pct: Decimal
    today_pnl: Decimal
    base_currency: str
    display_currency: str
    fx_source: str
    data_source: str
