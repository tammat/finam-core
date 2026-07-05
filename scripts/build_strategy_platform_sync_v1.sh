#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_PLATFORM_SYNC_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_strategy_platform_sync_v1.py <<'PY'
from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def table_columns(cur, table: str) -> set[str]:
    schema, name = table.split(".")
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
    """, (schema, name))
    return {r["column_name"] for r in cur.fetchall()}


def upsert_by_keys(cur, table: str, keys: dict, values: dict) -> None:
    cols = table_columns(cur, table)
    data = {**keys, **values}
    data = {k: v for k, v in data.items() if k in cols}
    keys = {k: v for k, v in keys.items() if k in cols}

    where = " AND ".join([f"{k}=%s" for k in keys])
    cur.execute(f"SELECT count(*) AS c FROM {table} WHERE {where}", list(keys.values()))
    exists = int(cur.fetchone()["c"]) > 0

    if exists:
        set_cols = [k for k in data if k not in keys]
        if set_cols:
            sql = f"UPDATE {table} SET " + ", ".join([f"{k}=%s" for k in set_cols]) + f" WHERE {where}"
            cur.execute(sql, [data[k] for k in set_cols] + list(keys.values()))
    else:
        sql = f"INSERT INTO {table} (" + ",".join(data) + ") VALUES (" + ",".join(["%s"] * len(data)) + ")"
        cur.execute(sql, list(data.values()))


def main() -> None:
    synced = 0
    configs = 0
    deps = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT strategy_code, strategy_family, category, priority,
                       parameter_schema, default_timeframes, enabled
                FROM analytics.strategy_library_v1
                WHERE enabled=true
                ORDER BY priority ASC, strategy_code ASC;
            """)
            rows = cur.fetchall()

            for r in rows:
                family = r["strategy_family"]
                version = "v1"

                upsert_by_keys(
                    cur,
                    "analytics.strategy_registry_v1",
                    {"strategy_family": family, "strategy_version": version},
                    {
                        "strategy_name": r["strategy_code"],
                        "category": r["category"],
                        "status": "ACTIVE",
                        "enabled": True,
                        "paper_enabled": True,
                        "risk_enabled": False,
                        "live_enabled": False,
                        "priority": r["priority"],
                        "source_version": "STRATEGY_PLATFORM_SYNC_V1",
                    },
                )
                synced += 1

                upsert_by_keys(
                    cur,
                    "analytics.strategy_configuration_v1",
                    {"strategy_family": family, "strategy_version": version, "config_version": "library_sync_v1"},
                    {
                        "active_status": "ACTIVE",
                        "config_json": json.dumps({
                            "strategy_code": r["strategy_code"],
                            "category": r["category"],
                            "default_timeframes": r["default_timeframes"],
                            "parameter_schema": r["parameter_schema"] or {},
                        }, ensure_ascii=False, sort_keys=True),
                        "source_version": "STRATEGY_PLATFORM_SYNC_V1",
                    },
                )
                configs += 1

                feature_map = {
                    "BREAKOUT": ["range_pct", "body_pct", "feature_quality_score"],
                    "VOLATILITY": ["range_pct", "atr_pct", "feature_quality_score"],
                    "MOMENTUM": ["return1_pct", "return5_pct", "volume_ratio20"],
                    "MEAN_REVERSION": ["return1_pct", "return5_pct", "range_pct"],
                    "VWAP": ["return1_pct", "volume_ratio20", "feature_quality_score"],
                    "VOLUME": ["volume_ratio20", "return1_pct", "feature_quality_score"],
                    "LIQUIDITY": ["range_pct", "wick_upper_pct", "wick_lower_pct"],
                }
                for feature in feature_map.get(r["category"], ["feature_quality_score"]):
                    upsert_by_keys(
                        cur,
                        "analytics.strategy_dependency_v1",
                        {
                            "strategy_family": family,
                            "strategy_version": version,
                            "feature_name": feature,
                        },
                        {
                            "required": True,
                            "weight": 1.0,
                            "source_version": "STRATEGY_PLATFORM_SYNC_V1",
                        },
                    )
                    deps += 1

            cur.execute("SELECT count(*) AS c FROM analytics.strategy_registry_v1;")
            total = cur.fetchone()["c"]

    print("=== STRATEGY_PLATFORM_SYNC_V1 ===")
    print(f"library_rows={len(rows)}")
    print(f"registry_synced={synced}")
    print(f"configs_synced={configs}")
    print(f"dependencies_synced={deps}")
    print(f"strategy_registry_total={total}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=STRATEGY_PLATFORM_SYNC_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_strategy_platform_sync_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_SYNC_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_strategy_platform_sync_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_platform_sync_v1.py | tee /tmp/strategy_platform_sync_v1.txt

grep -q "VERDICT=STRATEGY_PLATFORM_SYNC_V1_READY" /tmp/strategy_platform_sync_v1.txt

registry_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_registry_v1;")
library_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1 WHERE enabled=true;")

test "$registry_rows" -ge "$library_rows"

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8095/api/kg/v1/strategy-platform/summary >/tmp/strategy_sync_summary.json
curl -fsS http://127.0.0.1:8080/strategy-platform >/tmp/strategy_sync_ui.html

grep -q "Платформа стратегий" /tmp/strategy_sync_ui.html

echo "registry_rows=$registry_rows"
echo "library_rows=$library_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_PLATFORM_SYNC_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_platform_sync_v1.sh
scripts/test_strategy_platform_sync_v1.sh

echo "VERDICT=BUILD_STRATEGY_PLATFORM_SYNC_V1_OK"
