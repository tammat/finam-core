from __future__ import annotations

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    e.symbol,
                    e.strategy_code,
                    e.timeframe,
                    e.edge_score_v2,
                    e.model_verdict
                FROM analytics.edge_score_model_v2 e
                WHERE e.symbol IS NOT NULL
                  AND e.strategy_code IS NOT NULL
                  AND e.timeframe IS NOT NULL
                ORDER BY e.edge_score_v2 DESC NULLS LAST
            """)
            rows = cur.fetchall()

            bridged = 0

            for row in rows:
                symbol = row["symbol"]
                strategy_code = row["strategy_code"]
                timeframe = row["timeframe"]
                edge_score_v2 = row["edge_score_v2"]
                model_verdict = row["model_verdict"]

                cur.execute(
                    """
                    SELECT context_id, regime_code, confidence
                    FROM knowledge.market_context_v1
                    WHERE symbol=%s
                      AND timeframe=%s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (symbol, timeframe),
                )
                context = cur.fetchone()

                context_id = context["context_id"] if context else None
                regime_code = context["regime_code"] if context else "UNKNOWN"
                context_confidence = context["confidence"] if context else 0

                explanation = (
                    "Edge Score V2 candidate connected to Market Knowledge context. "
                    "Context is UNKNOWN until market context collector is populated."
                    if context is None
                    else "Edge Score V2 candidate connected to latest available market context."
                )

                cur.execute(
                    """
                    INSERT INTO knowledge.edge_context_v1
                    (
                        symbol,
                        strategy_code,
                        timeframe,
                        regime_code,
                        context_id,
                        edge_score_v2,
                        context_confidence,
                        context_verdict,
                        explanation,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        symbol,
                        strategy_code,
                        timeframe,
                        regime_code,
                        context_id,
                        edge_score_v2,
                        context_confidence,
                        model_verdict,
                        explanation,
                        SOURCE_VERSION,
                    ),
                )
                bridged += 1

    print("=== MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1 ===")
    print(f"bridged_rows={bridged}")
    print("edge_score_v2_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1_READY")


if __name__ == "__main__":
    main()
