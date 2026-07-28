from __future__ import annotations

import time
from typing import Any

from finam_core.strategy.regime_strategy_policy_v1 import RegimeStrategyDecisionV1


class DbRegimeStrategyPolicyV1:
    """Читает режимное назначение стратегии из БД и закрывается при ошибке."""

    def __init__(self, pg_logger: Any, cache_seconds: int = 60) -> None:
        self.pg_logger = pg_logger
        self.cache_seconds = max(1, int(cache_seconds))
        self._cache: dict[tuple[str, str], tuple[float, RegimeStrategyDecisionV1 | None]] = {}

    def resolve(
        self,
        *,
        asset_group: str,
        trend: str,
        data_ready: bool,
        stale: bool,
    ) -> RegimeStrategyDecisionV1 | None:
        if not data_ready or stale:
            return None

        key = (
            str(asset_group or "").strip().upper(),
            str(trend or "").strip().lower(),
        )
        if not all(key):
            return None

        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[0] < self.cache_seconds:
            return cached[1]

        decision: RegimeStrategyDecisionV1 | None = None
        try:
            with self.pg_logger._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select
                            strategy_code,
                            allowed_side,
                            countertrend_allowed,
                            minimum_cost_buffer,
                            exit_policy_code,
                            max_holding_bars
                        from analytics.regime_strategy_routing_policy_v1
                        where asset_group = %s
                          and regime_trend = %s
                          and active = true
                        limit 1
                        """,
                        key,
                    )
                    row = cur.fetchone()
            if row:
                decision = RegimeStrategyDecisionV1(
                    strategy_code=str(row[0]),
                    allowed_side=str(row[1]).upper(),
                    reason_code=f"DB_POLICY:{key[0]}:{key[1]}",
                    countertrend_allowed=bool(row[2]),
                    minimum_cost_buffer=float(row[3]),
                    exit_policy_code=str(row[4]),
                    max_holding_bars=int(row[5]),
                )
        except Exception:
            decision = None

        self._cache[key] = (now, decision)
        return decision
