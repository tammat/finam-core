from __future__ import annotations

import os


def get_br_rub_per_point(market_state: dict | None = None) -> float:
    """
    Русский комментарий:
    Production-расчет рублевой стоимости 1.00 пункта Brent:
    BR_USD_PER_POINT * USD/RUB.

    Источники USD/RUB по приоритету:
    1. market_state["usd_rub"]
    2. market_state["usdrub"]
    3. USD_RUB_RATE
    4. USD_RUB_RATE_FALLBACK
    """
    state = market_state or {}

    usd_per_point = float(os.getenv("BR_USD_PER_POINT", "10"))

    usd_rub_raw = (
        state.get("usd_rub")
        or state.get("usdrub")
        or os.getenv("USD_RUB_RATE")
        or os.getenv("USD_RUB_RATE_FALLBACK")
        or "80"
    )

    usd_rub = float(usd_rub_raw)

    return usd_per_point * usd_rub
