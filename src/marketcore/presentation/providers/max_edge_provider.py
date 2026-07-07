from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from marketcore.presentation.viewmodels.max_edge_viewmodel import MaxEdgeViewModel


class MaxEdgeProvider:
    def __init__(self, database_url: str | None = None, locale_code: str = "ru") -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")
        self.locale_code = locale_code

    def _labels(self, cur) -> dict:
        cur.execute(
            """
            SELECT resource_key, caption, caption_short, caption_mobile, icon, tooltip
            FROM presentation.ui_resource_v1
            WHERE resource_group='max_edge'
              AND locale_code=%s;
            """,
            (self.locale_code,),
        )
        return {r["resource_key"]: dict(r) for r in cur.fetchall()}

    def load(self, limit: int = 10) -> MaxEdgeViewModel:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                labels = self._labels(cur)

                cur.execute(
                    """
                    SELECT
                        rank_no,
                        candidate_id,
                        symbol,
                        strategy_code,
                        timeframe,
                        edge_score,
                        confidence,
                        expectancy,
                        profit_factor,
                        net_after_tax,
                        max_drawdown,
                        trades,
                        recommendation_code,
                        ranking_ts
                    FROM analytics.max_edge_ranking_v1
                    WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
                      AND status='ACTIVE'
                    ORDER BY ranking_ts DESC, rank_no ASC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                ranking = [dict(r) for r in cur.fetchall()]

        current = ranking[0] if ranking else {
            "rank_no": 0,
            "symbol": "NO_DATA",
            "strategy_code": "NO_DATA",
            "timeframe": "NO_DATA",
            "edge_score": 0,
            "confidence": 0,
            "recommendation_code": "COLLECT_MORE_DATA",
        }

        return MaxEdgeViewModel(
            current=current,
            ranking=ranking,
            labels=labels,
        )
