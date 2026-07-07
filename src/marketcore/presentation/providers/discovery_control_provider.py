from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from marketcore.presentation.viewmodels.discovery_control_viewmodel import DiscoveryControlViewModel


class DiscoveryControlProvider:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")

    def load(self) -> DiscoveryControlViewModel:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT enabled, config_json, updated_at
                    FROM analytics.edge_configuration_v1
                    WHERE edge_name='EDGE_DISCOVERY_LOOP'
                    LIMIT 1;
                """)
                config = dict(cur.fetchone() or {})
                cfg = dict(config.get("config_json") or {})

                cur.execute("""
                    SELECT count(*) AS unsafe_rows
                    FROM analytics.edge_candidate_v1
                    WHERE micro_live_allowed=true OR live_allowed=true;
                """)
                unsafe_rows = int((cur.fetchone() or {}).get("unsafe_rows") or 0)

                status = {
                    "enabled": config.get("enabled", False),
                    "profile": cfg.get("profile", ""),
                    "interval_minutes": cfg.get("interval_minutes", ""),
                    "auto_queue": cfg.get("auto_queue", False),
                    "unsafe_rows": unsafe_rows,
                    "updated_at": config.get("updated_at", ""),
                }

                cur.execute("""
                    SELECT status, count(*) AS rows
                    FROM analytics.edge_discovery_queue_v1
                    GROUP BY status
                    ORDER BY status;
                """)
                queue = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    SELECT result_status, count(*) AS rows
                    FROM analytics.edge_discovery_history_v1
                    WHERE source_version='EDGE_DISCOVERY_WORKER_V1'
                    GROUP BY result_status
                    ORDER BY result_status;
                """)
                worker = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    SELECT status, reason, queued_count, skipped_count, scheduler_ts
                    FROM analytics.edge_discovery_scheduler_v1
                    ORDER BY scheduler_ts DESC
                    LIMIT 1;
                """)
                scheduler = dict(cur.fetchone() or {})

                cur.execute("""
                    SELECT check_name, result, details, audit_ts
                    FROM analytics.edge_discovery_loop_audit_v1
                    WHERE source_version='EDGE_DISCOVERY_LOOP_AUDIT_V1'
                    ORDER BY audit_ts DESC, id DESC
                    LIMIT 12;
                """)
                audit = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    SELECT
                        pipeline_stage,
                        conversion_pct,
                        severity,
                        root_cause_code,
                        recommendation_code,
                        expected_gain_pct,
                        snapshot_ts
                    FROM analytics.edge_factory_bottleneck_v1
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                """)
                bottleneck = dict(cur.fetchone() or {})

                cur.execute("""
                    SELECT event_code, priority, status, expected_edge_gain, created_at
                    FROM analytics.edge_discovery_queue_v1
                    ORDER BY created_at DESC
                    LIMIT 20;
                """)
                events = [dict(r) for r in cur.fetchall()]

        actions = [
            {"command_code": "RUN_SCHEDULER", "caption": "Запустить планировщик"},
            {"command_code": "RUN_WORKER", "caption": "Запустить worker"},
            {"command_code": "RUN_AUDIT", "caption": "Запустить аудит"},
            {"command_code": "PAPER_REPRICE", "caption": "Пересчитать Paper"},
        ]

        return DiscoveryControlViewModel(
            status=status,
            queue=queue,
            worker=worker,
            scheduler=scheduler,
            audit=audit,
            bottleneck=bottleneck,
            events=events,
            actions=actions,
        )
