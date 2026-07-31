from __future__ import annotations

import logging
import time
from typing import Any

from finam_core.strategy.regime_strategy_policy_v1 import RegimeStrategyDecisionV1

LOG = logging.getLogger(__name__)


class DbRegimeStrategyPolicyV1:
    """Читает режимное назначение стратегии из БД и закрывается при ошибке."""

    def __init__(self, pg_logger: Any, cache_seconds: int = 60) -> None:
        self.pg_logger = pg_logger
        self.cache_seconds = max(1, int(cache_seconds))
        self._cache: dict[tuple[str, str], tuple[float, RegimeStrategyDecisionV1 | None]] = {}
        self._resolution_status: dict[tuple[str, str], str] = {}

    def resolution_status(self, *, asset_group: str, trend: str) -> str:
        key = (
            str(asset_group or "").strip().upper(),
            str(trend or "").strip().lower(),
        )
        return self._resolution_status.get(key, "NOT_QUERIED")

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
            self._resolution_status[key] = "FOUND" if cached[1] is not None else "NOT_ROUTED"
            return cached[1]

        decision: RegimeStrategyDecisionV1 | None = None
        query_succeeded = False
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
            query_succeeded = True
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
            self._resolution_status[key] = "FOUND" if decision is not None else "NOT_ROUTED"
        except Exception:
            # Временный сбой БД не равен отсутствующей политике. Не прячем
            # первопричину и не удерживаем ложный fail-closed результат 60 секунд.
            LOG.exception(
                "FUTURES_DB_POLICY_QUERY_FAILED asset_group=%s trend=%s",
                key[0],
                key[1],
            )
            self._resolution_status[key] = "QUERY_FAILED"

        if query_succeeded:
            self._cache[key] = (now, decision)
        return decision
