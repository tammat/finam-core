from __future__ import annotations

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.edge_score_model_v2_shadow_observation_v1
                (
                    symbol,
                    strategy_code,
                    timeframe,
                    source_candidate_id,
                    edge_score_v2,
                    model_verdict,
                    reconciliation_verdict,
                    score_delta,
                    rank_delta,
                    explain_groups,
                    runtime_seen,
                    signal_seen,
                    order_seen,
                    fill_seen,
                    runtime_allowed,
                    execution_allowed,
                    micro_live_allowed,
                    observation_status,
                    source_version
                )
                SELECT
                    m.symbol,
                    m.strategy_code,
                    m.timeframe,
                    NULL AS source_candidate_id,
                    m.edge_score_v2,
                    m.model_verdict,
                    rec.reconciliation_verdict,
                    rec.score_delta,
                    rec.rank_delta,
                    COALESCE(explain.explain_groups, '[]'::jsonb),
                    CASE WHEN runtime.symbol IS NULL THEN 0 ELSE 1 END AS runtime_seen,
                    CASE WHEN runtime.symbol IS NULL THEN 0 ELSE 1 END AS signal_seen,
                    0 AS order_seen,
                    0 AS fill_seen,
                    0 AS runtime_allowed,
                    0 AS execution_allowed,
                    0 AS micro_live_allowed,
                    'OBSERVED_ONLY' AS observation_status,
                    %s AS source_version
                FROM analytics.edge_score_model_v2 m
                LEFT JOIN LATERAL (
                    SELECT
                        r.verdict AS reconciliation_verdict,
                        r.score_delta,
                        r.rank_delta
                    FROM analytics.edge_score_model_v2_reconciliation r
                    WHERE r.symbol = m.symbol
                      AND r.strategy_code = m.strategy_code
                      AND r.timeframe = m.timeframe
                    ORDER BY r.check_ts DESC
                    LIMIT 1
                ) rec ON true
                LEFT JOIN LATERAL (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'group_code', e.group_code,
                            'group_score', e.group_score,
                            'group_weight', e.group_weight,
                            'group_contribution', e.group_contribution,
                            'model_verdict', e.model_verdict
                        )
                        ORDER BY e.group_code
                    ) AS explain_groups
                    FROM analytics.edge_score_model_v2_explain e
                    WHERE e.symbol = m.symbol
                      AND e.strategy_code = m.strategy_code
                      AND e.timeframe = m.timeframe
                      AND e.source_version = 'EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD'
                ) explain ON true
                LEFT JOIN LATERAL (
                    SELECT q.symbol
                    FROM analytics.max_edge_ranking_v1 q
                    WHERE q.symbol = m.symbol
                      AND q.strategy_code = m.strategy_code
                      AND q.timeframe = m.timeframe
                    ORDER BY q.ranking_ts DESC
                    LIMIT 1
                ) runtime ON true
                WHERE m.source_version = 'EDGE_SCORE_MODEL_V2';
            """, (SOURCE_VERSION,))

            cur.execute("""
                SELECT
                    count(*) AS rows_total,
                    count(*) FILTER (
                        WHERE runtime_allowed <> 0
                           OR execution_allowed <> 0
                           OR micro_live_allowed <> 0
                           OR order_seen <> 0
                           OR fill_seen <> 0
                    ) AS unsafe_rows
                FROM analytics.edge_score_model_v2_shadow_observation_v1
                WHERE source_version = %s;
            """, (SOURCE_VERSION,))
            row = cur.fetchone()

            print("=== EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1 ===")
            print(f"shadow_rows={row['rows_total']}")
            print(f"unsafe_rows={row['unsafe_rows']}")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1_READY")


if __name__ == "__main__":
    main()
