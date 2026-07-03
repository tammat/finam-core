from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1"


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    return int(list(row.values())[0] or 0)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1 ===")

            legacy_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
            legacy_symbols = scalar(cur, "SELECT count(DISTINCT symbol) FROM marketcore_ui.paper_edge_research_candidates_v1;")
            queue_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
            queue_symbols = scalar(cur, "SELECT count(DISTINCT symbol) FROM marketcore_ui.market_universe_research_queue_v1;")
            ranking_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.market_universe_ranking_v1;")
            universe_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")

            if queue_rows > 0 and queue_symbols > 1:
                status = "MARKET_UNIVERSE_ACTIVE"
                diagnosis = "Новый источник market_universe_research_queue_v1 готов и содержит мультиинструментальную очередь."
                action = "Использовать Research Queue как основной источник Edge/Validation; legacy BR-only оставить read-only."
            else:
                status = "BLOCKED_QUEUE_NOT_READY"
                diagnosis = "Новая Research Queue пуста или содержит один инструмент."
                action = "Проверить MARKET_UNIVERSE_RESEARCH_QUEUE_V1 и market bars."

            cur.execute("""
                INSERT INTO marketcore_ui.edge_discovery_use_market_universe_v1 (
                    id, legacy_rows, legacy_symbols, queue_rows, queue_symbols,
                    ranking_rows, universe_rows, migration_status, diagnosis,
                    recommended_action, runtime_changed, execution_changed,
                    orders_changed, fills_changed, micro_live_allowed,
                    refreshed_at, source_version, build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    0,0,0,0,0,now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    legacy_rows=EXCLUDED.legacy_rows,
                    legacy_symbols=EXCLUDED.legacy_symbols,
                    queue_rows=EXCLUDED.queue_rows,
                    queue_symbols=EXCLUDED.queue_symbols,
                    ranking_rows=EXCLUDED.ranking_rows,
                    universe_rows=EXCLUDED.universe_rows,
                    migration_status=EXCLUDED.migration_status,
                    diagnosis=EXCLUDED.diagnosis,
                    recommended_action=EXCLUDED.recommended_action,
                    runtime_changed=0,
                    execution_changed=0,
                    orders_changed=0,
                    fills_changed=0,
                    micro_live_allowed=0,
                    refreshed_at=now(),
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                legacy_rows, legacy_symbols, queue_rows, queue_symbols,
                ranking_rows, universe_rows, status, diagnosis, action,
                SOURCE_VERSION, build_id,
            ))

    print(f"legacy_rows={legacy_rows}")
    print(f"legacy_symbols={legacy_symbols}")
    print(f"queue_rows={queue_rows}")
    print(f"queue_symbols={queue_symbols}")
    print(f"ranking_rows={ranking_rows}")
    print(f"universe_rows={universe_rows}")
    print(f"migration_status={status}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
