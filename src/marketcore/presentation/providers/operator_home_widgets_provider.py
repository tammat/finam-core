from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from marketcore.presentation.widgets.contracts import WidgetViewModel
from marketcore.presentation.widgets.registry import default_widget_registry


def _count(cur, table_name: str) -> int:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (table_name,))
    if not cur.fetchone()["exists"]:
        return 0
    cur.execute(f"SELECT count(*) AS c FROM {table_name}")
    return int(cur.fetchone()["c"] or 0)


def _best_edge(cur) -> dict:
    cur.execute("SELECT to_regclass('analytics.edge_score_model_v2') IS NOT NULL AS exists")
    if not cur.fetchone()["exists"]:
        return {}

    cur.execute("""
        SELECT symbol, strategy_code, timeframe, edge_score_v2, model_verdict
        FROM analytics.edge_score_model_v2
        ORDER BY edge_score_v2 DESC NULLS LAST
        LIMIT 1
    """)
    return dict(cur.fetchone() or {})


class OperatorHomeWidgetsProvider:
    def load(self) -> list[WidgetViewModel]:
        updated_at = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%y %H:%M")
        registry = default_widget_registry()

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                best = _best_edge(cur)
                edge_rows = _count(cur, "analytics.edge_score_model_v2")
                shadow_rows = _count(cur, "analytics.edge_score_model_v2_shadow_observation_v1")
                daily_rows = _count(cur, "analytics.edge_score_model_v2_shadow_observation_daily_v1")

        items = {item.widget_id: item for item in registry.all()}

        return [
            WidgetViewModel(
                widget_id="best_edge",
                title_key=items["best_edge"].title_key,
                icon=items["best_edge"].icon,
                priority=items["best_edge"].priority,
                category=items["best_edge"].category,
                content={
                    "symbol": best.get("symbol", "N/A"),
                    "strategy": best.get("strategy_code", "N/A"),
                    "timeframe": best.get("timeframe", "N/A"),
                    "score": best.get("edge_score_v2", "N/A"),
                    "verdict": best.get("model_verdict", "N/A"),
                },
                updated_at=updated_at,
            ),
            WidgetViewModel(
                widget_id="shadow",
                title_key=items["shadow"].title_key,
                icon=items["shadow"].icon,
                priority=items["shadow"].priority,
                category=items["shadow"].category,
                content={
                    "rows": shadow_rows,
                    "mode": "readonly",
                    "execution_allowed": 0,
                },
                updated_at=updated_at,
            ),
            WidgetViewModel(
                widget_id="daily",
                title_key=items["daily"].title_key,
                icon=items["daily"].icon,
                priority=items["daily"].priority,
                category=items["daily"].category,
                content={
                    "rows": daily_rows,
                    "mode": "daily analytics",
                    "execution_allowed": 0,
                },
                updated_at=updated_at,
            ),
            WidgetViewModel(
                widget_id="portfolio",
                title_key=items["portfolio"].title_key,
                icon=items["portfolio"].icon,
                priority=items["portfolio"].priority,
                category=items["portfolio"].category,
                content={
                    "portfolio_value": "0,00 ₽",
                    "daily_pnl": "0,00 ₽",
                    "mode": "readonly",
                },
                updated_at=updated_at,
            ),
            WidgetViewModel(
                widget_id="system",
                title_key=items["system"].title_key,
                icon=items["system"].icon,
                priority=items["system"].priority,
                category=items["system"].category,
                content={
                    "research_rows": edge_rows,
                    "runtime_allowed": 0,
                    "execution_allowed": 0,
                    "micro_live_allowed": 0,
                },
                updated_at=updated_at,
            ),
        ]
