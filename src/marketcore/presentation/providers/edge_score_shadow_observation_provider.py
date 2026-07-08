from __future__ import annotations

import psycopg2
import psycopg2.extras


class EdgeScoreShadowObservationProvider:
    def load(self, limit: int = 50) -> dict:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        observed_at,
                        symbol,
                        strategy_code,
                        timeframe,
                        edge_score_v2,
                        model_verdict,
                        reconciliation_verdict,
                        score_delta,
                        rank_delta,
                        runtime_seen,
                        signal_seen,
                        order_seen,
                        fill_seen,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed,
                        observation_status
                    FROM analytics.edge_score_model_v2_shadow_observation_v1
                    WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1'
                    ORDER BY observed_at DESC, edge_score_v2 DESC
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
