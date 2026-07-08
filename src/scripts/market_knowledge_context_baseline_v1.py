from __future__ import annotations

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT symbol, timeframe
                FROM analytics.edge_score_model_v2
                WHERE symbol IS NOT NULL
                  AND timeframe IS NOT NULL
                ORDER BY symbol, timeframe
            """)
            rows = cur.fetchall()

            inserted = 0

            for row in rows:
                cur.execute(
                    """
                    INSERT INTO knowledge.market_context_v1
                    (
                        symbol,
                        regime_code,
                        context_date,
                        timeframe,
                        volatility_state,
                        liquidity_state,
                        volume_state,
                        spread_state,
                        correlation_state,
                        sector_strength_state,
                        session_state,
                        confidence,
                        evidence_json,
                        source_version
                    )
                    VALUES
                    (
                        %s,
                        'UNKNOWN',
                        current_date,
                        %s,
                        'UNKNOWN',
                        'UNKNOWN',
                        'UNKNOWN',
                        'UNKNOWN',
                        'UNKNOWN',
                        'UNKNOWN',
                        'UNKNOWN',
                        0,
                        jsonb_build_object(
                            'reason', 'baseline_context_until_market_context_collector_ready',
                            'symbol', %s,
                            'timeframe', %s
                        ),
                        %s
                    )
                    """,
                    (
                        row["symbol"],
                        row["timeframe"],
                        row["symbol"],
                        row["timeframe"],
                        SOURCE_VERSION,
                    ),
                )
                inserted += 1

    print("=== MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1 ===")
    print(f"baseline_context_rows={inserted}")
    print("edge_score_v2_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_MARKET_KNOWLEDGE_CONTEXT_BASELINE_V1_READY")


if __name__ == "__main__":
    main()
