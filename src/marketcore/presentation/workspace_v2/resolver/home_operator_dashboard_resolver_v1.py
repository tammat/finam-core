from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.domain.home_operator_dashboard_model_v1 import (
    HomeOperatorDashboardItemV1,
)
from marketcore.presentation.workspace_v2.mapper.home_status_mapper_v1 import (
    HomeStatusScalarMapperV1,
)


class HomeOperatorDashboardResolverV1:
    SOURCES = (
        (
            "model_health",
            "home.operator.model_health.title",
            "home.operator.model_health.subtitle",
            ("analytics.marketcore_model_health_snapshot_v1",),
        ),
        (
            "recommendations",
            "home.operator.recommendations.title",
            "home.operator.recommendations.subtitle",
            ("analytics.marketcore_model_health_recommendation_v1", "analytics.recommendation_score_v1"),
        ),
        (
            "signal_funnel",
            "home.operator.signal_funnel.title",
            "home.operator.signal_funnel.subtitle",
            ("analytics.signal_funnel_snapshot_v1", "analytics.signal_funnel_reason_snapshot_v1"),
        ),
        (
            "risk",
            "home.operator.risk.title",
            "home.operator.risk.subtitle",
            ("analytics.risk_decision_snapshot_v1", "public.risk_event_audit_v1"),
        ),
        (
            "events",
            "home.operator.events.title",
            "home.operator.events.subtitle",
            ("public.event_store", "public.events", "public.execution_events"),
        ),
    )

    def __init__(self) -> None:
        self._cache: tuple[HomeOperatorDashboardItemV1, ...] | None = None

    def resolve(self) -> tuple[HomeOperatorDashboardItemV1, ...]:
        if self._cache is not None:
            return self._cache

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                items = tuple(
                    self._item(cur, item_code, title_key, subtitle_key, table_names)
                    for item_code, title_key, subtitle_key, table_names in self.SOURCES
                )

        self._cache = items
        return items

    def _item(
        self,
        cur: Any,
        item_code: str,
        title_key: str,
        subtitle_key: str,
        table_names: tuple[str, ...],
    ) -> HomeOperatorDashboardItemV1:
        rows_total = sum(self._safe_count(cur, table_name) for table_name in table_names)
        status_code = UiStatusCode.OK if rows_total > 0 else UiStatusCode.WARNING

        return HomeOperatorDashboardItemV1(
            item_code=item_code,
            title_key=title_key,
            subtitle_key=subtitle_key,
            status_code=status_code,
            status_label_key=self._status_label_key(status_code),
            rows_total=rows_total,
            updated_at=self._updated_at(cur, table_names),
        )

    def _updated_at(
        self,
        cur: Any,
        table_names: tuple[str, ...],
    ) -> str:
        for table_name in table_names:
            if not self._table_exists(cur, table_name):
                continue

            schema_name, object_name = table_name.split(".", 1)

            cur.execute(
                """
                SELECT pg_stat_get_last_analyze_time(c.oid) AS ts
                FROM pg_class c
                JOIN pg_namespace n
                  ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relname = %s
                """,
                (schema_name, object_name),
            )

            row = cur.fetchone()
            if row and row["ts"]:
                return str(row["ts"])

        return ""

    def _safe_count(self, cur: Any, table_name: str) -> int:
        if not self._table_exists(cur, table_name):
            return 0

        schema_name, object_name = table_name.split(".", 1)

        cur.execute(
            sql.SQL("SELECT count(*) AS rows_total FROM {}.{}").format(
                sql.Identifier(schema_name),
                sql.Identifier(object_name),
            )
        )
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
        return "ui.status.warning"
