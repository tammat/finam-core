#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


CALCULATION_VERSION = "WORKFLOW_DIMENSION_BUILDER_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def build_dim_stage(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.dim_stage_v1 (
            stage_code,
            stage_order,
            label_ru,
            short_label_ru,
            full_label_ru,
            health_light,
            is_active,
            source_table,
            calculation_version,
            calculated_at,
            payload,
            updated_at
        )
        SELECT
            s.stage_code,
            s.stage_order,
            coalesce(l.label, s.stage_code) AS label_ru,
            coalesce(l.short_label, l.label, s.stage_code) AS short_label_ru,
            coalesce(l.full_label, l.label, s.stage_code) AS full_label_ru,
            coalesce(s.payload->>'default_light_code', 'BLUE') AS health_light,
            s.is_active,
            'reference.workflow_stages_v1',
            %s,
            now(),
            jsonb_build_object(
                'source','WORKFLOW_DIMENSION_BUILDER_V1',
                'dimension','dim_stage_v1',
                'localization','ru_RU',
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now()
        FROM reference.workflow_stages_v1 s
        LEFT JOIN reference.localization_labels_v1 l
          ON l.entity_type='workflow_stage'
         AND l.entity_code=s.stage_code
         AND l.locale_code='ru_RU'
         AND l.is_active=true
        ON CONFLICT(stage_code) DO UPDATE SET
            stage_order=EXCLUDED.stage_order,
            label_ru=EXCLUDED.label_ru,
            short_label_ru=EXCLUDED.short_label_ru,
            full_label_ru=EXCLUDED.full_label_ru,
            health_light=EXCLUDED.health_light,
            is_active=EXCLUDED.is_active,
            source_table=EXCLUDED.source_table,
            calculation_version=EXCLUDED.calculation_version,
            calculated_at=now(),
            payload=EXCLUDED.payload,
            updated_at=now()
    """, (CALCULATION_VERSION,))
    return int(cur.rowcount)


def build_dim_status_light(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.dim_status_light_v1 (
            light_code,
            priority,
            icon,
            hex_color,
            label_ru,
            short_label_ru,
            is_active,
            source_table,
            calculation_version,
            calculated_at,
            payload,
            updated_at
        )
        SELECT
            sl.light_code,
            sl.priority,
            sl.icon,
            sl.hex_color,
            coalesce(l.label, sl.light_code) AS label_ru,
            coalesce(l.short_label, l.label, sl.light_code) AS short_label_ru,
            sl.is_active,
            'reference.status_lights_v1',
            %s,
            now(),
            jsonb_build_object(
                'source','WORKFLOW_DIMENSION_BUILDER_V1',
                'dimension','dim_status_light_v1',
                'localization','ru_RU',
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now()
        FROM reference.status_lights_v1 sl
        LEFT JOIN reference.localization_labels_v1 l
          ON l.entity_type='status_light'
         AND l.entity_code=sl.light_code
         AND l.locale_code='ru_RU'
         AND l.is_active=true
        ON CONFLICT(light_code) DO UPDATE SET
            priority=EXCLUDED.priority,
            icon=EXCLUDED.icon,
            hex_color=EXCLUDED.hex_color,
            label_ru=EXCLUDED.label_ru,
            short_label_ru=EXCLUDED.short_label_ru,
            is_active=EXCLUDED.is_active,
            source_table=EXCLUDED.source_table,
            calculation_version=EXCLUDED.calculation_version,
            calculated_at=now(),
            payload=EXCLUDED.payload,
            updated_at=now()
    """, (CALCULATION_VERSION,))
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                stage_rows = build_dim_stage(cur)
                light_rows = build_dim_status_light(cur)
                conn.commit()
            else:
                stage_rows = 0
                light_rows = 0
                conn.rollback()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.dim_stage_v1")
            stage_total = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.dim_status_light_v1")
            light_total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT stage_code, label_ru, short_label_ru, health_light
                FROM warehouse.dim_stage_v1
                WHERE stage_code='RISK'
                LIMIT 1
            """)
            risk = cur.fetchone()

            cur.execute("""
                SELECT light_code, icon, label_ru, hex_color
                FROM warehouse.dim_status_light_v1
                WHERE light_code='GREEN'
                LIMIT 1
            """)
            green = cur.fetchone()

    print("=== WORKFLOW_DIMENSION_BUILDER_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"dim_stage_rows_changed={stage_rows}")
    print(f"dim_status_light_rows_changed={light_rows}")
    print(f"dim_stage_total={stage_total}")
    print(f"dim_status_light_total={light_total}")

    if risk:
        print(
            "dim_stage_risk="
            f"{risk['stage_code']}|"
            f"{risk['label_ru']}|"
            f"{risk['short_label_ru']}|"
            f"{risk['health_light']}"
        )

    if green:
        print(
            "dim_light_green="
            f"{green['light_code']}|"
            f"{green['icon']}|"
            f"{green['label_ru']}|"
            f"{green['hex_color']}"
        )

    print("dimension_policy=REFERENCE_ENRICHED_LOOKUPS")
    print("localization_policy=RU_LABELS_FROM_REFERENCE")
    print("fallback_policy=USE_CODE_IF_LABEL_MISSING")
    print("fact_policy=FACTS_STORE_CODES_ONLY")
    print("mart_policy=MART_USES_DIMENSIONS_FOR_LABELS")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_DIMENSION_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
