from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_UNIVERSE_RESEARCH_QUEUE_V1"
TOP_LIMIT = int(os.getenv("MARKET_UNIVERSE_RESEARCH_QUEUE_LIMIT", "20"))


def strategy_family(asset_class: str, timeframe: str) -> str:
    if asset_class == "FUTURES":
        return "BREAKOUT_MOMENTUM"
    if asset_class == "EQUITY_OR_FX_SPOT":
        return "VOLATILITY_BREAKOUT"
    if asset_class == "CRYPTO_PROXY":
        return "TREND_MOMENTUM"
    if asset_class == "INDEX":
        return "REGIME_FILTER"
    return "BASELINE_RESEARCH"


def priority(rank: int, score: float) -> str:
    if rank <= 5 and score >= 80:
        return "HIGH"
    if rank <= 10:
        return "MEDIUM"
    return "NORMAL"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MARKET_UNIVERSE_RESEARCH_QUEUE_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.market_universe_research_queue_v1;")

            cur.execute("""
                SELECT
                    rank,
                    symbol,
                    timeframe,
                    asset_class,
                    total_score,
                    ranking_status
                FROM marketcore_ui.market_universe_ranking_v1
                WHERE ranking_status IN ('READY_FOR_RESEARCH', 'WATCHLIST')
                ORDER BY
                    CASE ranking_status
                        WHEN 'READY_FOR_RESEARCH' THEN 1
                        WHEN 'WATCHLIST' THEN 2
                        ELSE 9
                    END,
                    total_score DESC,
                    rank
                LIMIT %s;
            """, (TOP_LIMIT,))

            rows = [dict(r) for r in cur.fetchall()]

            for qrank, row in enumerate(rows, start=1):
                score = float(row["total_score"] or 0)
                pr = priority(qrank, score)
                family = strategy_family(row["asset_class"], row["timeframe"])

                cur.execute("""
                    INSERT INTO marketcore_ui.market_universe_research_queue_v1 (
                        queue_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        total_score,
                        ranking_status,
                        research_priority,
                        research_status,
                        recommended_strategy_family,
                        recommended_action,
                        source_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,'QUEUED',%s,%s,%s,%s,now(),%s
                    );
                """, (
                    qrank,
                    row["symbol"],
                    row["timeframe"],
                    row["asset_class"],
                    row["total_score"],
                    row["ranking_status"],
                    pr,
                    family,
                    "Запустить research discovery по инструменту и timeframe.",
                    row["rank"],
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.market_universe_research_queue_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT research_priority, recommended_strategy_family, count(*) AS rows
                FROM marketcore_ui.market_universe_research_queue_v1
                GROUP BY research_priority, recommended_strategy_family
                ORDER BY research_priority, recommended_strategy_family;
            """)
            groups = cur.fetchall()

    print(f"rows_written={rows_written}")
    print(f"top_limit={TOP_LIMIT}")
    for g in groups:
        print(
            f"GROUP priority={g['research_priority']} "
            f"strategy_family={g['recommended_strategy_family']} "
            f"rows={g['rows']}"
        )
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_V1_READY")


if __name__ == "__main__":
    main()
