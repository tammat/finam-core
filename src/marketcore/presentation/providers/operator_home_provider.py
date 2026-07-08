from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from marketcore.presentation.dashboard.viewmodel import (
    AlertItem,
    DashboardViewModel,
    KpiItem,
    SafetyModel,
    TableColumn,
    TableModel,
    ToolbarItem,
)


def _count(cur, table_name: str) -> int:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (table_name,))
    if not cur.fetchone()["exists"]:
        return 0
    cur.execute(f"SELECT count(*) AS c FROM {table_name}")
    return int(cur.fetchone()["c"] or 0)


def _latest_score(cur) -> dict:
    cur.execute("""
        SELECT to_regclass('analytics.edge_score_model_v2') IS NOT NULL AS exists
    """)
    if not cur.fetchone()["exists"]:
        return {}

    cur.execute("""
        SELECT symbol, strategy_code, timeframe, edge_score_v2, model_verdict
        FROM analytics.edge_score_model_v2
        ORDER BY edge_score_v2 DESC NULLS LAST
        LIMIT 1
    """)
    return dict(cur.fetchone() or {})


class OperatorHomeProvider:
    def load(self) -> DashboardViewModel:
        now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%y %H:%M")

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                best = _latest_score(cur)
                edge_rows = _count(cur, "analytics.edge_score_model_v2")
                shadow_rows = _count(cur, "analytics.edge_score_model_v2_shadow_observation_v1")
                daily_rows = _count(cur, "analytics.edge_score_model_v2_shadow_observation_daily_v1")

        rows = [
            {
                "section": "Best Edge",
                "status": best.get("symbol", "N/A"),
                "value": best.get("edge_score_v2", "N/A"),
                "details": best.get("strategy_code", "N/A"),
            },
            {
                "section": "Shadow",
                "status": "readonly",
                "value": shadow_rows,
                "details": "runtime_allowed=0 execution_allowed=0",
            },
            {
                "section": "Daily Analytics",
                "status": "readonly",
                "value": daily_rows,
                "details": "daily observations",
            },
            {
                "section": "Research",
                "status": "active",
                "value": edge_rows,
                "details": "edge score rows",
            },
            {
                "section": "System",
                "status": "safe",
                "value": "OK",
                "details": "execution disabled",
            },
        ]

        return DashboardViewModel(
            dashboard_id="operator.home",
            title_key="page.operator_home.title",
            subtitle_key="page.operator_home.subtitle",
            icon="🧠",
            updated_at=now,
            toolbar=[
                ToolbarItem("home", "button.home", "🏠", "/"),
                ToolbarItem("refresh", "button.refresh", "🔄", "/"),
                ToolbarItem("max_edge", "page.max_edge.title", "🎯", "/max-edge"),
                ToolbarItem("shadow", "page.shadow.title", "👁️", "/edge-score-shadow"),
                ToolbarItem("daily", "page.shadow.daily.title", "📊", "/edge-score-shadow-daily"),
            ],
            kpis=[
                KpiItem("runtime", "runtime.allowed", 0, "tooltip.runtime.disabled", "neutral", "🛡"),
                KpiItem("execution", "runtime.execution_allowed", 0, "tooltip.execution.disabled", "neutral", "🔒"),
                KpiItem("shadow", "dashboard.shadow.rows", shadow_rows, "tooltip.shadow.rows", "neutral", "👁️"),
                KpiItem("daily", "dashboard.daily.rows", daily_rows, "tooltip.daily.rows", "neutral", "📊"),
            ],
            alerts=[
                AlertItem("execution_disabled", "status.disabled", "message.execution.disabled", "info", "🔒"),
                AlertItem("runtime_disabled", "status.disabled", "message.runtime.disabled", "info", "🛡"),
            ],
            table=TableModel(
                columns=[
                    TableColumn("section", "column.section"),
                    TableColumn("status", "column.status"),
                    TableColumn("value", "column.value"),
                    TableColumn("details", "column.details"),
                ],
                rows=rows,
                rows_count=len(rows),
                empty_message_key="message.empty",
            ),
            footer={
                "source": "OperatorHomeProvider",
                "source_version": "MARKETCORE_OPERATOR_HOME_IMPLEMENTATION_V1",
            },
            safety=SafetyModel(
                runtime_allowed=0,
                execution_allowed=0,
                micro_live_allowed=0,
                orders_changed=0,
                fills_changed=0,
            ),
        )
