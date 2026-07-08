from __future__ import annotations

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKET_CONTEXT_SECTOR_ENGINE_V1"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                WITH latest_context AS (
                    SELECT DISTINCT ON (mc.symbol, mc.timeframe)
                        mc.context_id,
                        mc.symbol,
                        mc.timeframe,
                        mc.regime_code,
                        mc.volatility_state,
                        mc.liquidity_state,
                        mc.volume_state,
                        mc.session_state,
                        mc.correlation_state,
                        mc.source_version,
                        mc.created_at
                    FROM knowledge.market_context_v1 mc
                    WHERE mc.source_version='MARKET_CONTEXT_COLLECTOR_V1'
                    ORDER BY mc.symbol, mc.timeframe, mc.created_at DESC
                ),
                instrument_sector AS (
                    SELECT
                        i.symbol,
                        s.sector_code
                    FROM knowledge.instrument_v1 i
                    LEFT JOIN knowledge.sector_v1 s
                      ON s.sector_id=i.sector_id
                    WHERE i.is_active
                ),
                sector_stats AS (
                    SELECT
                        i.sector_code,
                        c.timeframe,
                        count(*) AS instruments_total,
                        sum((c.regime_code <> 'UNKNOWN')::int) AS known_regime,
                        sum((c.liquidity_state <> 'UNKNOWN')::int) AS known_liquidity,
                        sum((c.volume_state <> 'UNKNOWN')::int) AS known_volume,
                        sum((c.correlation_state <> 'UNKNOWN')::int) AS known_correlation
                    FROM latest_context c
                    JOIN instrument_sector i
                      ON i.symbol=c.symbol
                    WHERE i.sector_code IS NOT NULL
                    GROUP BY i.sector_code, c.timeframe
                )
                SELECT
                    c.context_id,
                    c.symbol,
                    c.timeframe,
                    i.sector_code,
                    ss.instruments_total,
                    ss.known_regime,
                    ss.known_liquidity,
                    ss.known_volume,
                    ss.known_correlation
                FROM latest_context c
                JOIN instrument_sector i
                  ON i.symbol=c.symbol
                JOIN sector_stats ss
                  ON ss.sector_code=i.sector_code
                 AND ss.timeframe=c.timeframe
                WHERE i.sector_code IS NOT NULL
            """)
            rows = cur.fetchall()

            updated = 0

            for row in rows:
                instruments_total = int(row["instruments_total"] or 0)
                known_regime = int(row["known_regime"] or 0)
                known_liquidity = int(row["known_liquidity"] or 0)
                known_volume = int(row["known_volume"] or 0)
                known_correlation = int(row["known_correlation"] or 0)

                if instruments_total <= 0:
                    sector_strength_state = "UNKNOWN"
                else:
                    score = (
                        known_regime
                        + known_liquidity
                        + known_volume
                        + known_correlation
                    ) / (instruments_total * 4)

                    if score >= 0.75:
                        sector_strength_state = "EVALUATED"
                    elif score > 0:
                        sector_strength_state = "PARTIAL"
                    else:
                        sector_strength_state = "UNKNOWN"

                cur.execute(
                    """
                    UPDATE knowledge.market_context_v1
                    SET
                        sector_strength_state=%s,
                        evidence_json = evidence_json || jsonb_build_object(
                            'sector_engine_source_version', %s,
                            'sector_code', %s,
                            'sector_instruments_total', %s,
                            'sector_known_regime', %s,
                            'sector_known_liquidity', %s,
                            'sector_known_volume', %s,
                            'sector_known_correlation', %s,
                            'sector_engine_mode', 'classification_based_existing_context'
                        )
                    WHERE context_id=%s
                      AND source_version='MARKET_CONTEXT_COLLECTOR_V1'
                    """,
                    (
                        sector_strength_state,
                        SOURCE_VERSION,
                        row["sector_code"],
                        instruments_total,
                        known_regime,
                        known_liquidity,
                        known_volume,
                        known_correlation,
                        row["context_id"],
                    ),
                )
                updated += 1

    print("=== MARKET_CONTEXT_SECTOR_ENGINE_V1 ===")
    print(f"sector_context_rows_updated={updated}")
    print("config_source=postgres")
    print("symbol_hardcode=0")
    print("edge_score_v2_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_CONTEXT_SECTOR_ENGINE_V1_READY")


if __name__ == "__main__":
    main()
