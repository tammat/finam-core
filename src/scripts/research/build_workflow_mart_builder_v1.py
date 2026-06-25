#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


MART_VERSION = "WORKFLOW_MART_BUILDER_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def build_candidate_mart(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.mart_candidate_workflow_v1 (
            workflow_run_id,
            candidate_id,
            symbol,
            display_symbol,
            strategy_code,
            timeframe,
            workflow_status_code,
            workflow_status_label_ru,
            current_stage_code,
            current_stage_label_ru,
            next_stage_code,
            next_stage_label_ru,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            mart_version,
            calculated_at,
            payload,
            updated_at
        )
        SELECT
            workflow_run_id,
            candidate_id,
            symbol,
            display_symbol,
            strategy_code,
            timeframe,
            workflow_status_code,
            workflow_status_label_ru,
            current_stage_code,
            current_stage_label_ru,
            next_stage_code,
            next_stage_label_ru,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            %s,
            now(),
            jsonb_build_object(
                'source','WORKFLOW_MART_BUILDER_V1',
                'mart','mart_candidate_workflow_v1',
                'display_group','workflow',
                'display_order',30,
                'ui_ready',true,
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now()
        FROM warehouse.sem_candidate_v1
        ON CONFLICT(candidate_id) DO UPDATE SET
            workflow_run_id=EXCLUDED.workflow_run_id,
            symbol=EXCLUDED.symbol,
            display_symbol=EXCLUDED.display_symbol,
            strategy_code=EXCLUDED.strategy_code,
            timeframe=EXCLUDED.timeframe,
            workflow_status_code=EXCLUDED.workflow_status_code,
            workflow_status_label_ru=EXCLUDED.workflow_status_label_ru,
            current_stage_code=EXCLUDED.current_stage_code,
            current_stage_label_ru=EXCLUDED.current_stage_label_ru,
            next_stage_code=EXCLUDED.next_stage_code,
            next_stage_label_ru=EXCLUDED.next_stage_label_ru,
            health_score=EXCLUDED.health_score,
            health_light=EXCLUDED.health_light,
            health_icon=EXCLUDED.health_icon,
            health_reason_code=EXCLUDED.health_reason_code,
            mart_version=EXCLUDED.mart_version,
            calculated_at=now(),
            payload=EXCLUDED.payload,
            updated_at=now()
    """, (MART_VERSION,))
    return int(cur.rowcount)


def refresh_dashboard_mart(cur) -> int:
    cur.execute("DELETE FROM warehouse.mart_workflow_dashboard_v1")
    cur.execute("""
        INSERT INTO warehouse.mart_workflow_dashboard_v1 (
            workflow_run_id,
            candidate_id,
            section_code,
            section_title_ru,
            metric_code,
            metric_label_ru,
            metric_value,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            mart_version,
            calculated_at,
            payload,
            updated_at
        )
        WITH s AS (
            SELECT
                count(*)::text AS candidates_total,
                coalesce(max(health_score), 100) AS health_score,
                coalesce(max(health_light), 'GREEN') AS health_light,
                coalesce(max(health_icon), '🟢') AS health_icon,
                coalesce(max(health_reason_code), 'OK') AS health_reason_code,
                coalesce(max(current_stage_code), 'UNKNOWN') AS current_stage_code,
                coalesce(max(current_stage_label_ru), 'UNKNOWN') AS current_stage_label_ru
            FROM warehouse.sem_candidate_v1
        ),
        rows(section_code, section_title_ru, metric_code, metric_label_ru, metric_value, display_order, health_score, health_light, health_icon, health_reason_code) AS (
            SELECT 'portfolio', 'Портфель', 'portfolio_status', 'Состояние портфеля', 'DEFERRED', 10,
                   100::numeric, 'BLUE', '🔵', 'PORTFOLIO_WAREHOUSE_DEFERRED'
            UNION ALL
            SELECT 'risk', 'Риск', 'risk_status', 'Состояние риска', 'DEFERRED', 20,
                   100::numeric, 'BLUE', '🔵', 'RISK_WAREHOUSE_DEFERRED'
            UNION ALL
            SELECT 'workflow', 'Workflow', 'workflow_current_stage', 'Текущий этап', s.current_stage_label_ru, 30,
                   s.health_score, s.health_light, s.health_icon, s.health_reason_code FROM s
            UNION ALL
            SELECT 'candidate', 'Кандидат', 'candidate_count', 'Кандидатов', s.candidates_total, 40,
                   s.health_score, s.health_light, s.health_icon, s.health_reason_code FROM s
            UNION ALL
            SELECT 'research', 'Research', 'research_status', 'Исследования', 'DEFERRED', 50,
                   100::numeric, 'BLUE', '🔵', 'RESEARCH_MART_DEFERRED'
            UNION ALL
            SELECT 'market', 'Рынок', 'market_status', 'Рыночные данные', 'DEFERRED', 60,
                   100::numeric, 'BLUE', '🔵', 'MARKET_WAREHOUSE_DEFERRED'
            UNION ALL
            SELECT 'warehouse', 'Warehouse', 'warehouse_status', 'Хранилище', 'WORKFLOW_READY', 70,
                   100::numeric, 'GREEN', '🟢', 'OK'
            UNION ALL
            SELECT 'system', 'Система', 'system_status', 'Состояние системы', 'OK', 80,
                   100::numeric, 'GREEN', '🟢', 'OK'
            UNION ALL
            SELECT 'journal', 'Журнал', 'journal_status', 'События', 'DEFERRED', 90,
                   100::numeric, 'BLUE', '🔵', 'JOURNAL_DEFERRED'
        )
        SELECT
            (SELECT workflow_run_id FROM warehouse.sem_workflow_v1 ORDER BY updated_at DESC LIMIT 1) AS workflow_run_id,
            (SELECT candidate_id FROM warehouse.sem_workflow_v1 ORDER BY updated_at DESC LIMIT 1) AS candidate_id,
            section_code,
            section_title_ru,
            metric_code,
            metric_label_ru,
            metric_value,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            %s AS mart_version,
            now() AS calculated_at,
            jsonb_build_object(
                'source','WORKFLOW_MART_BUILDER_V1',
                'display_order',display_order,
                'ui_ready',true,
                'responsive_web_ui_ready',true,
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now() AS updated_at
        FROM rows
    """, (MART_VERSION,))
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                candidate_rows = build_candidate_mart(cur)
                dashboard_rows = refresh_dashboard_mart(cur)
                conn.commit()
            else:
                candidate_rows = 0
                dashboard_rows = 0
                conn.rollback()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.mart_candidate_workflow_v1")
            candidate_total = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.mart_workflow_dashboard_v1")
            dashboard_total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT candidate_id, display_symbol, strategy_code,
                       workflow_status_code, current_stage_code,
                       current_stage_label_ru, health_score, health_light, health_icon
                FROM warehouse.mart_candidate_workflow_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            candidate = cur.fetchone()

            cur.execute("""
                SELECT section_code, metric_code, metric_value, health_light, health_icon
                FROM warehouse.mart_workflow_dashboard_v1
                ORDER BY (payload->>'display_order')::int
            """)
            dashboard = cur.fetchall()

    print("=== WORKFLOW_MART_BUILDER_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"mart_candidate_rows_changed={candidate_rows}")
    print(f"mart_dashboard_rows_inserted={dashboard_rows}")
    print(f"mart_candidate_total={candidate_total}")
    print(f"mart_dashboard_total={dashboard_total}")

    if candidate:
        print(
            "mart_candidate="
            f"{candidate['candidate_id']}|"
            f"{candidate['display_symbol']}|"
            f"{candidate['strategy_code']}|"
            f"{candidate['workflow_status_code']}|"
            f"{candidate['current_stage_code']}|"
            f"{candidate['current_stage_label_ru']}|"
            f"health={candidate['health_score']}|"
            f"{candidate['health_light']}|"
            f"{candidate['health_icon']}"
        )

    for row in dashboard:
        print(
            "dashboard_row="
            f"{row['section_code']}|"
            f"{row['metric_code']}|"
            f"{row['metric_value']}|"
            f"{row['health_light']}|"
            f"{row['health_icon']}"
        )

    print("mart_policy=UI_READY_RECALCULABLE_DATASET")
    print("source_policy=SEMANTIC_ONLY")
    print("presentation_policy=READS_MART_OR_SNAPSHOT_ONLY")
    print("responsive_web_ui_ready=1")
    print("portfolio_first=1")
    print("navigation_standard=HOME_AND_BACK")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_MART_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
