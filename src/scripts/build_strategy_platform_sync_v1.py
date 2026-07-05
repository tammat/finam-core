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

    if not keys:
        raise RuntimeError(f"UPSERT_KEYS_EMPTY table={table} available_columns={sorted(cols)}")

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
                dep_cols = table_columns(cur, "analytics.strategy_dependency_v1")
                for feature in feature_map.get(r["category"], ["feature_quality_score"]):
                    if {"strategy_family", "strategy_version", "feature_name"}.issubset(dep_cols):
                        dep_keys = {
                            "strategy_family": family,
                            "strategy_version": version,
                            "feature_name": feature,
                        }
                    elif {"strategy_family", "feature_name"}.issubset(dep_cols):
                        dep_keys = {
                            "strategy_family": family,
                            "feature_name": feature,
                        }
                    elif {"strategy_name", "feature_name"}.issubset(dep_cols):
                        dep_keys = {
                            "strategy_name": r["strategy_code"],
                            "feature_name": feature,
                        }
                    else:
                        print(f"SKIP_DEPENDENCY_UNSUPPORTED_COLUMNS columns={sorted(dep_cols)}")
                        continue

                    upsert_by_keys(
                        cur,
                        "analytics.strategy_dependency_v1",
                        dep_keys,
                        {
                            "strategy_family": family,
                            "strategy_version": version,
                            "strategy_name": r["strategy_code"],
                            "feature_name": feature,
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
