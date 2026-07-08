from __future__ import annotations

import psycopg2
import psycopg2.extras


class EdgeScoreShadowDailyProvider:
    def load(self, limit: int = 50) -> dict:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        trade_date,
                        symbol,
                        strategy_code,
                        timeframe,
                        observations_count,
                        runtime_seen_count,
                        signal_seen_count,
                        order_seen_count,
                        fill_seen_count,
                        avg_edge_score_v2,
                        min_edge_score_v2,
                        max_edge_score_v2,
                        pass_count,
                        review_count,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    FROM analytics.edge_score_model_v2_shadow_observation_daily_v1
                    WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1'
                    ORDER BY trade_date DESC, avg_edge_score_v2 DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]

        return {
            "rows": rows,
            "rows_total": len(rows),
            "runtime_allowed": 0,
            "execution_allowed": 0,
            "micro_live_allowed": 0,
        }
