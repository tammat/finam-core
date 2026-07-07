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
                        r.rank_no,
                        r.candidate_id,
                        r.symbol,
                        r.strategy_code,
                        r.timeframe,
                        r.edge_score,
                        v2.edge_score_v2,
                        v2.economic_score,
                        v2.reliability_score,
                        v2.execution_score,
                        v2.risk_score,
                        rec.reconciliation_verdict,
                        rec.score_delta,
                        rec.rank_delta,
                        r.confidence,
                        r.expectancy,
                        r.profit_factor,
                        r.net_after_tax,
                        r.max_drawdown,
                        r.trades,
                        r.recommendation_code,
                        r.ranking_ts
                    FROM analytics.max_edge_ranking_v1 r
                    LEFT JOIN analytics.edge_score_model_v2 v2
                      ON v2.symbol = r.symbol
                     AND v2.strategy_code = r.strategy_code
                     AND v2.timeframe = r.timeframe
                    LEFT JOIN LATERAL (
                        SELECT
                            rr.verdict AS reconciliation_verdict,
                            rr.score_delta,
                            rr.rank_delta
                        FROM analytics.edge_score_model_v2_reconciliation rr
                        WHERE rr.symbol = r.symbol
                          AND rr.strategy_code = r.strategy_code
                          AND rr.timeframe = r.timeframe
                        ORDER BY rr.check_ts DESC
                        LIMIT 1
                    ) rec ON true
                    WHERE r.source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
                      AND r.status='ACTIVE'
                    ORDER BY r.ranking_ts DESC, r.rank_no ASC
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
