from __future__ import annotations

import os
import subprocess
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_HEALTH_V1"


def timer_status() -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "finam-feature-store.timer"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def main() -> None:
    build_id = str(uuid.uuid4())
    timer = timer_status()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    count(*)::bigint AS feature_rows,
                    count(DISTINCT symbol)::bigint AS feature_symbols,
                    max(bar_ts) AS latest_bar_ts,
                    max(refreshed_at) AS latest_refreshed_at,
                    max(freshness_sec)::int AS max_freshness_sec,
                    count(*) FILTER (WHERE return1_pct IS NOT NULL)::bigint AS with_return1,
                    count(*) FILTER (WHERE volume_ratio20 IS NOT NULL)::bigint AS with_volume_ratio20
                FROM analytics.feature_snapshot_v1;
            """)
            r = cur.fetchone()

            rows = int(r["feature_rows"] or 0)
            symbols = int(r["feature_symbols"] or 0)
            with_return1 = int(r["with_return1"] or 0)
            with_volume = int(r["with_volume_ratio20"] or 0)
            max_freshness = r["max_freshness_sec"]

            if rows <= 0:
                status = "FAILED"
                diagnosis = "Feature Store пуст."
                action = "Запустить FEATURE_STORE_HISTORY_BACKFILL_V1."
            elif timer != "active":
                status = "DEGRADED"
                diagnosis = "Таймер Feature Store не активен."
                action = "Проверить systemctl status finam-feature-store.timer."
            elif with_return1 <= 0 or with_volume <= 0:
                status = "DEGRADED"
                diagnosis = "Исторические признаки заполнены не полностью."
                action = "Перезапустить finam-feature-store.service."
            else:
                status = "HEALTHY"
                diagnosis = "Feature Store заполнен, исторические признаки есть, таймер активен."
                action = "Действий не требуется."

            cur.execute("""
                INSERT INTO analytics.feature_store_health_v1 (
                    health_id,
                    feature_rows,
                    feature_symbols,
                    latest_bar_ts,
                    latest_refreshed_at,
                    max_freshness_sec,
                    with_return1,
                    with_volume_ratio20,
                    timer_active,
                    health_status,
                    diagnosis,
                    recommended_action,
                    source_version,
                    build_id,
                    refreshed_at
                )
                VALUES (
                    'GLOBAL', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                )
                ON CONFLICT (health_id) DO UPDATE SET
                    feature_rows=EXCLUDED.feature_rows,
                    feature_symbols=EXCLUDED.feature_symbols,
                    latest_bar_ts=EXCLUDED.latest_bar_ts,
                    latest_refreshed_at=EXCLUDED.latest_refreshed_at,
                    max_freshness_sec=EXCLUDED.max_freshness_sec,
                    with_return1=EXCLUDED.with_return1,
                    with_volume_ratio20=EXCLUDED.with_volume_ratio20,
                    timer_active=EXCLUDED.timer_active,
                    health_status=EXCLUDED.health_status,
                    diagnosis=EXCLUDED.diagnosis,
                    recommended_action=EXCLUDED.recommended_action,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (
                rows,
                symbols,
                r["latest_bar_ts"],
                r["latest_refreshed_at"],
                max_freshness,
                with_return1,
                with_volume,
                timer,
                status,
                diagnosis,
                action,
                SOURCE_VERSION,
                build_id,
            ))

    print("=== FEATURE_STORE_HEALTH_V1 ===")
    print(f"feature_rows={rows}")
    print(f"feature_symbols={symbols}")
    print(f"with_return1={with_return1}")
    print(f"with_volume_ratio20={with_volume}")
    print(f"timer_active={timer}")
    print(f"health_status={status}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_STORE_HEALTH_V1_READY")


if __name__ == "__main__":
    main()
