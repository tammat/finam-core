from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

from marketcore.presentation.framework.mapper.portfolio_mapper import PortfolioRowMapperV1
from marketcore.presentation.workspace_v2.domain.portfolio_model_v1 import PortfolioSnapshotV1


class PortfolioV2Resolver:
    SUMMARY_VIEW = "public.v_real_portfolio_summary_ru"
    POSITIONS_VIEW = "public.v_real_portfolio_positions_ru"
    DASHBOARD_VIEW = "public.v_positions_dashboard_ru"
    VISUALIZATION_VIEW = "public.v_portfolio_visualization_ru"

    def __init__(self) -> None:
        self._cache: PortfolioSnapshotV1 | None = None

    def resolve(self, limit: int = 200) -> PortfolioSnapshotV1:
        if self._cache is not None:
            return self._cache

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                summary = self._fetch_view(cur, self.SUMMARY_VIEW, 20)
                positions = self._fetch_view(cur, self.POSITIONS_VIEW, limit)
                dashboard = self._fetch_view(cur, self.DASHBOARD_VIEW, limit)
                visualization = self._fetch_view(cur, self.VISUALIZATION_VIEW, limit)

        snapshot = PortfolioSnapshotV1(
            summary=PortfolioRowMapperV1.rows_to_domain(self.SUMMARY_VIEW, summary),
            positions=PortfolioRowMapperV1.rows_to_domain(self.POSITIONS_VIEW, positions),
            dashboard=PortfolioRowMapperV1.rows_to_domain(self.DASHBOARD_VIEW, dashboard),
            visualization=PortfolioRowMapperV1.rows_to_domain(self.VISUALIZATION_VIEW, visualization),
        )
        self._cache = snapshot
        return snapshot

    def _fetch_view(self, cur: Any, full_name: str, limit: int) -> list[Any]:
        if not self._view_exists(cur, full_name):
            return []

        schema_name, view_name = full_name.split(".", 1)

        cur.execute(
            sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
                sql.Identifier(schema_name),
                sql.Identifier(view_name),
            ),
            (limit,),
        )
        return list(cur.fetchall())

    def _view_exists(self, cur: Any, full_name: str) -> bool:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (full_name,))
        result = cur.fetchone()
        return bool(result["ok"])
