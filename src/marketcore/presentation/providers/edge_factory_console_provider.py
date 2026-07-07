from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


class EdgeFactoryConsoleProvider:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")

    def load(self) -> dict:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT rank_no, symbol, strategy_code, timeframe, edge_score,
                           confidence, trades, recommendation_code, ranking_ts
                    FROM analytics.max_edge_ranking_v1
                    WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
                      AND status='ACTIVE'
                    ORDER BY ranking_ts DESC, rank_no ASC
                    LIMIT 10;
                """)
                max_edge = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    SELECT pipeline_stage, conversion_pct, severity,
                           root_cause_code, recommendation_code, expected_gain_pct, snapshot_ts
                    FROM analytics.edge_factory_bottleneck_v1
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                """)
                bottleneck = dict(cur.fetchone() or {})

                cur.execute("""
                    SELECT status, count(*) AS rows
                    FROM analytics.edge_discovery_queue_v1
                    GROUP BY status
                    ORDER BY status;
                """)
                queue = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    SELECT command_status, count(*) AS rows
                    FROM presentation.command_queue_v1
                    GROUP BY command_status
                    ORDER BY command_status;
                """)
                commands = [dict(r) for r in cur.fetchall()]

        return {
            "max_edge": max_edge,
            "bottleneck": bottleneck,
            "queue": queue,
            "commands": commands,
            "actions": [
                {"command_code": "RUN_SCHEDULER", "caption": "Запустить планировщик"},
                {"command_code": "RUN_WORKER", "caption": "Запустить worker"},
                {"command_code": "RUN_AUDIT", "caption": "Запустить аудит"},
                {"command_code": "PAPER_REPRICE", "caption": "Пересчитать Paper"},
            ],
        }
