from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from storage.decision_funnel_read_model import (
    build_decision_funnel_read_model,
)


def build_read_model(
    database_url: str,
    *,
    hours: int = 24,
    now: datetime | None = None,
    symbol: str | None = None,
    strategy: str | None = None,
    timeframe: str | None = None,
    recent_limit: int = 50,
    reason_limit: int = 20,
    dimension_limit: int = 100,
) -> dict[str, Any]:
    """
    Построить read-only представление Decision Funnel.

    Функция только читает analytics.signal_decision_funnel_v1.
    Runtime, execution, ордера и торговые решения не изменяются.
    """

    def connection_factory():
        return psycopg2.connect(
            database_url,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )

    model = build_decision_funnel_read_model(
        connection_factory,
        hours=hours,
        now=now,
        symbol=symbol,
        strategy=strategy,
        timeframe=timeframe,
        recent_limit=recent_limit,
        reason_limit=reason_limit,
        dimension_limit=dimension_limit,
    )

    # Дополнительный API-контракт безопасности.
    model["read_only"] = True

    metadata = model.setdefault("metadata", {})
    metadata.update(
        {
            "source": (
                "analytics.signal_decision_funnel_v1"
            ),
            "logic": "DECISION_FUNNEL_KG_API_V1",
            "ui_direct_sql": 0,
            "write_actions_allowed": 0,
            "systemctl_actions_allowed": 0,
            "runtime_instrumentation": 0,
            "execution_actions_allowed": 0,
        }
    )

    return model
