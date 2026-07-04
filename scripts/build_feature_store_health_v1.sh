#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_FEATURE_STORE_HEALTH_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/005_feature_store_health_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.feature_store_health_v1 (
    health_id TEXT PRIMARY KEY DEFAULT 'GLOBAL',
    feature_rows BIGINT NOT NULL DEFAULT 0,
    feature_symbols BIGINT NOT NULL DEFAULT 0,
    latest_bar_ts TIMESTAMPTZ,
    latest_refreshed_at TIMESTAMPTZ,
    max_freshness_sec INTEGER,
    with_return1 BIGINT NOT NULL DEFAULT 0,
    with_volume_ratio20 BIGINT NOT NULL DEFAULT 0,
    timer_active TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'FEATURE_STORE_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_feature_store_health_v1.py <<'PY'
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
PY

cat > scripts/test_feature_store_health_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_HEALTH_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/005_feature_store_health_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_feature_store_health_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_store_health_v1.py | tee /tmp/feature_store_health_v1.txt

grep -q "VERDICT=FEATURE_STORE_HEALTH_V1_READY" /tmp/feature_store_health_v1.txt

rows=$(psql -At -d finam_core -c "SELECT feature_rows FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")
status=$(psql -At -d finam_core -c "SELECT health_status FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")
timer=$(psql -At -d finam_core -c "SELECT timer_active FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")

test "$rows" -gt 0
test "$status" = "HEALTHY"
test "$timer" = "active"

psql -d finam_core -c "
SELECT *
FROM analytics.feature_store_health_v1;
"

echo "feature_rows=$rows"
echo "health_status=$status"
echo "timer_active=$timer"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_HEALTH_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_HEALTH_V1_OK"
SH_TEST

chmod +x scripts/test_feature_store_health_v1.sh
scripts/test_feature_store_health_v1.sh

echo "VERDICT=BUILD_FEATURE_STORE_HEALTH_V1_OK"
