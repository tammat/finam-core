from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.domain.home_status_model_v1 import HomeStatusItemV1
from marketcore.presentation.workspace_v2.mapper.home_status_mapper_v1 import (
    HomeStatusScalarMapperV1,
)


class HomeStatusResolverV1:
    SYSTEM_TABLES = ("presentation.ui_theme_v1", "presentation.ui_resource_v1")
    PORTFOLIO_TABLES = (
        "presentation.v_workspace_v2_portfolio_positions_ru",
        "public.v_real_portfolio_summary_ru",
    )
    RESEARCH_TABLES = ("public.strategy_research_results", "public.runtime_candidate_scorecard")
    PROBE_TABLES = ("public.grafana_closed_trade_paper_only", "public.paper_source_cleanup_plan_v1")
    OBSERVATION_TABLES = (
        "public.runtime_shadow_observation_v1",
        "public.shadow_runtime_observations",
        "public.runtime_observations",
    )
    RUNTIME_TABLES = ("public.runtime_active_universe", "public.runtime_config")

    def __init__(self) -> None:
        self._cache: tuple[HomeStatusItemV1, ...] | None = None

    def resolve(self) -> tuple[HomeStatusItemV1, ...]:
        if self._cache is not None:
            return self._cache

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                items = (
                    self._item(cur, "system", "home.card.status.system.title", self.SYSTEM_TABLES),
                    self._item(cur, "portfolio", "home.card.status.portfolio.title", self.PORTFOLIO_TABLES),
                    self._item(cur, "research", "home.card.status.research.title", self.RESEARCH_TABLES),
                    self._item(cur, "probe", "home.card.status.probe.title", self.PROBE_TABLES),
                    self._item(cur, "observation", "home.card.status.observation.title", self.OBSERVATION_TABLES),
                    self._runtime_item(cur),
                )

        self._cache = items
        return items

    def _item(
        self,
        cur: Any,
        item_code: str,
        title_key: str,
        table_names: tuple[str, ...],
    ) -> HomeStatusItemV1:
        rows_total = sum(self._safe_count(cur, table_name) for table_name in table_names)
        status_code = UiStatusCode.OK if rows_total > 0 else UiStatusCode.WARNING
        subtitle_key = (
            "home.card.status.ready.subtitle"
            if rows_total > 0
            else "home.card.status.pending.subtitle"
        )
        return HomeStatusItemV1(
            item_code=item_code,
            title_key=title_key,
            subtitle_key=subtitle_key,
            status_code=status_code,
            status_label_key=self._status_label_key(status_code),
            rows_total=rows_total,
            updated_at=self._updated_at(cur, table_names),
        )

    def _runtime_item(self, cur: Any) -> HomeStatusItemV1:
        rows_total = sum(self._safe_count(cur, table_name) for table_name in self.RUNTIME_TABLES)
        status_code = UiStatusCode.BLOCKED
        return HomeStatusItemV1(
            item_code="runtime",
            title_key="home.card.status.runtime.title",
            subtitle_key="home.card.status.blocked.subtitle",
            status_code=status_code,
            status_label_key=self._status_label_key(status_code),
            rows_total=rows_total,
            updated_at=self._updated_at(cur, self.RUNTIME_TABLES),
        )

    def _updated_at(
        self,
        cur: Any,
        table_names: tuple[str, ...],
    ) -> str:

        for table_name in table_names:

            if not self._table_exists(cur, table_name):
                continue

            schema_name, object_name = table_name.split(".",1)

            cur.execute(
                """
                SELECT pg_stat_get_last_analyze_time(c.oid) AS ts
                FROM pg_class c
                JOIN pg_namespace n
                  ON n.oid=c.relnamespace
                WHERE n.nspname=%s
                  AND c.relname=%s
                """,
                (
                    schema_name,
                    object_name,
                ),
            )

            row=cur.fetchone()

            if row and row["ts"]:
                return str(row["ts"])

        return ""

    def _safe_count(self, cur: Any, table_name: str) -> int:
        if not self._table_exists(cur, table_name):
            return 0

        cur.execute(f"SELECT count(*) AS rows_total FROM {table_name}")
        row = cur.fetchone()
        return HomeStatusScalarMapperV1.int_value(row, "rows_total")

    def _table_exists(self, cur: Any, table_name: str) -> bool:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (table_name,))
        row = cur.fetchone()
        return HomeStatusScalarMapperV1.bool_value(row, "ok")

    @staticmethod
    def _status_label_key(status_code: UiStatusCode) -> str:
        if status_code == UiStatusCode.OK:
            return "ui.status.ok"
        if status_code == UiStatusCode.BLOCKED:
            return "ui.status.blocked"
        return "ui.status.warning"
