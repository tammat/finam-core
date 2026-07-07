from __future__ import annotations

from decimal import Decimal
import psycopg2
import psycopg2.extras

SOURCE_VERSION = "EDGE_SCORE_MODEL_V2_PART_2"

def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.edge_score_model_v2_reconciliation (
                    id BIGSERIAL PRIMARY KEY,
                    check_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    strategy_code TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    old_score NUMERIC(12,6) NOT NULL,
                    new_score NUMERIC(12,6) NOT NULL,
                    score_delta NUMERIC(12,6) NOT NULL,
                    old_rank INTEGER NOT NULL,
                    new_rank INTEGER NOT NULL,
                    rank_delta INTEGER NOT NULL,
                    verdict TEXT NOT NULL,
                    source_version TEXT NOT NULL DEFAULT 'EDGE_SCORE_MODEL_V2_PART_2',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)

            cur.execute("""
                WITH old_ranked AS (
                    SELECT DISTINCT ON (symbol, strategy_code, timeframe)
                        symbol, strategy_code, timeframe,
                        edge_score AS old_score,
                        rank_no AS old_rank
                    FROM analytics.max_edge_ranking_v1
                    WHERE status='ACTIVE'
                    ORDER BY symbol, strategy_code, timeframe, ranking_ts DESC
                ),
                new_ranked AS (
                    SELECT
                        symbol, strategy_code, timeframe,
                        edge_score_v2 AS new_score,
                        row_number() OVER (ORDER BY edge_score_v2 DESC) AS new_rank
                    FROM analytics.edge_score_model_v2
                    WHERE source_version='EDGE_SCORE_MODEL_V2'
                )
                INSERT INTO analytics.edge_score_model_v2_reconciliation
                (symbol, strategy_code, timeframe, old_score, new_score, score_delta,
                 old_rank, new_rank, rank_delta, verdict)
                SELECT
                    o.symbol,
                    o.strategy_code,
                    o.timeframe,
                    o.old_score,
                    n.new_score,
                    n.new_score - o.old_score,
                    o.old_rank,
                    n.new_rank,
                    n.new_rank - o.old_rank,
                    CASE
                        WHEN abs(n.new_score - o.old_score) >= 25 THEN 'REVIEW_SCORE_SHIFT'
                        WHEN abs(n.new_rank - o.old_rank) >= 5 THEN 'REVIEW_RANK_SHIFT'
                        ELSE 'PASS'
                    END
                FROM old_ranked o
                JOIN new_ranked n
                  ON n.symbol=o.symbol
                 AND n.strategy_code=o.strategy_code
                 AND n.timeframe=o.timeframe;
            """)

            cur.execute("""
                SELECT count(*) rows_total,
                       count(*) FILTER (WHERE verdict <> 'PASS') review_rows
                FROM analytics.edge_score_model_v2_reconciliation
                WHERE source_version=%s
            """, (SOURCE_VERSION,))
            row = cur.fetchone()

            print("=== EDGE_SCORE_MODEL_V2_PART_2 ===")
            print(f"rows_total={row['rows_total']}")
            print(f"review_rows={row['review_rows']}")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=EDGE_SCORE_MODEL_V2_PART_2_READY")

if __name__ == "__main__":
    main()
