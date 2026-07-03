from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.edge_validation_use_market_universe_v1;")

            cur.execute("""
                SELECT
                    queue_rank,
                    symbol,
                    timeframe,
                    asset_class,
                    total_score,
                    research_priority,
                    ranking_status,
                    recommended_strategy_family
                FROM marketcore_ui.market_universe_research_queue_v1
                ORDER BY queue_rank
                LIMIT 50;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            for rank, r in enumerate(rows, start=1):
                priority = str(r.get("research_priority") or "")
                score = r.get("total_score") or 0
                strategy = r.get("recommended_strategy_family") or "MARKET_UNIVERSE_EDGE"

                if priority == "HIGH":
                    status = "READY_FOR_VALIDATION"
                    action = "Передать в проверку edge по новой Market Universe queue."
                elif priority == "MEDIUM":
                    status = "WATCH_VALIDATION"
                    action = "Оставить в очереди проверки после HIGH-кандидатов."
                else:
                    status = "WAIT_PRIORITY"
                    action = "Ждать повышения рейтинга или свежих данных."

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_validation_use_market_universe_v1 (
                        validation_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        strategy,
                        side,
                        source_queue_rank,
                        total_score,
                        research_priority,
                        ranking_status,
                        validation_status,
                        validation_stage,
                        recommended_action,
                        runtime_changed,
                        execution_changed,
                        orders_changed,
                        fills_changed,
                        micro_live_allowed,
                        refreshed_at,
                        source_version,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,'ANY',%s,%s,%s,%s,%s,'QUEUE',%s,
                        0,0,0,0,0,now(),%s,%s
                    );
                """, (
                    rank,
                    r.get("symbol") or "",
                    r.get("timeframe") or "",
                    r.get("asset_class") or "",
                    strategy,
                    r.get("queue_rank"),
                    score,
                    priority,
                    r.get("ranking_status") or "",
                    status,
                    action,
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_validation_use_market_universe_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT validation_status, count(*) AS rows
                FROM marketcore_ui.edge_validation_use_market_universe_v1
                GROUP BY validation_status
                ORDER BY validation_status;
            """)
            groups = cur.fetchall()

            cur.execute("""
                SELECT count(DISTINCT symbol) AS symbols
                FROM marketcore_ui.edge_validation_use_market_universe_v1;
            """)
            symbols = int(cur.fetchone()["symbols"] or 0)

    print(f"rows_written={rows_written}")
    print(f"symbols={symbols}")
    for g in groups:
        print(f"validation_status_{g['validation_status']}={g['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
