from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras


class ProfitFactoryKpiServiceV1:
    ALLOWED_SCOPES = frozenset({"REAL", "TEST"})

    def __init__(self, dsn: str = "postgresql:///finam_core") -> None:
        self._dsn = dsn

    def summary(self, *, scope: str = "REAL") -> dict[str, Any]:
        normalized_scope = self._scope(scope)
        with psycopg2.connect(self._dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT data_scope, eligible_candidates, capital_allocated,
                           expected_profit, realized_profit, profit_gap,
                           expected_roi, realized_roi, refreshed_at
                    FROM analytics.profit_factory_kpi_summary_v1
                    WHERE data_scope=%s
                """, (normalized_scope,))
                row = cur.fetchone()
        return dict(row) if row else self._empty_summary(normalized_scope)

    def candidates(self, *, scope: str = "REAL") -> list[dict[str, Any]]:
        normalized_scope = self._scope(scope)
        with psycopg2.connect(self._dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT candidate_id, strategy_code, symbol, timeframe,
                           data_scope, data_quality_status,
                           financial_kpi_eligible, allocation_status,
                           capital_allocated, currency_code, expected_profit,
                           realized_profit, profit_gap, expected_roi,
                           realized_roi, measurement_from, measurement_to,
                           refreshed_at
                    FROM analytics.profit_factory_kpi_candidate_v1
                    WHERE data_scope=%s
                    ORDER BY expected_profit DESC, candidate_id
                """, (normalized_scope,))
                return [dict(row) for row in cur.fetchall()]

    @classmethod
    def _scope(cls, scope: str) -> str:
        normalized_scope = str(scope or "REAL").upper()
        if normalized_scope not in cls.ALLOWED_SCOPES:
            raise ValueError(f"invalid data scope: {scope}")
        return normalized_scope

    @staticmethod
    def _empty_summary(scope: str) -> dict[str, Any]:
        return {
            "data_scope": scope,
            "eligible_candidates": 0,
            "capital_allocated": 0,
            "expected_profit": 0,
            "realized_profit": 0,
            "profit_gap": 0,
            "expected_roi": 0,
            "realized_roi": 0,
            "refreshed_at": None,
        }
