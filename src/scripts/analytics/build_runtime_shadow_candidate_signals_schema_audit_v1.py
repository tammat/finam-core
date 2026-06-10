#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

TABLE = "runtime_shadow_candidate_signals_v1"

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME SHADOW CANDIDATE SIGNALS SCHEMA AUDIT V1 ===")
    print("mode=schema_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"table={TABLE}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT to_regclass(%s) IS NOT NULL AS table_exists;
            """, (f"public.{TABLE}",))
            table_exists = bool(cur.fetchone()["table_exists"])

            cur.execute("""
                SELECT column_name, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name=%s
                ORDER BY ordinal_position;
            """, (TABLE,))
            columns = cur.fetchall()

            cur.execute("""
                SELECT
                    conname,
                    pg_get_constraintdef(c.oid) AS constraint_def
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname='public'
                  AND t.relname=%s
                  AND c.contype='u'
                ORDER BY conname;
            """, (TABLE,))
            uniques = cur.fetchall()

    colmap = {r["column_name"]: r for r in columns}

    required = [
        "id", "created_at", "symbol", "root", "strategy", "timeframe",
        "signal_ts", "side", "entry_price", "qty",
        "shadow_only", "runtime_allow", "execution_enabled",
        "reason", "source", "raw_json",
    ]

    missing = [c for c in required if c not in colmap]

    shadow_default = str(colmap.get("shadow_only", {}).get("column_default", ""))
    runtime_default = str(colmap.get("runtime_allow", {}).get("column_default", ""))
    execution_default = str(colmap.get("execution_enabled", {}).get("column_default", ""))

    unique_ok = any(
        "symbol" in r["constraint_def"]
        and "strategy" in r["constraint_def"]
        and "timeframe" in r["constraint_def"]
        and "signal_ts" in r["constraint_def"]
        and "side" in r["constraint_def"]
        for r in uniques
    )

    shadow_default_ok = "1" in shadow_default
    runtime_default_ok = "0" in runtime_default
    execution_default_ok = "0" in execution_default

    print("TABLE_ROW "
          f"table_exists={int(table_exists)} "
          f"columns={len(columns)} "
          f"missing={','.join(missing) if missing else 'none'}")

    print("DEFAULT_ROW "
          f"shadow_only_default={shadow_default} "
          f"shadow_only_ok={int(shadow_default_ok)} "
          f"runtime_allow_default={runtime_default} "
          f"runtime_allow_ok={int(runtime_default_ok)} "
          f"execution_enabled_default={execution_default} "
          f"execution_enabled_ok={int(execution_default_ok)}")

    print("UNIQUE_ROWS")
    for r in uniques:
        print(f"UNIQUE_ROW name={r['conname']} def={r['constraint_def']}")

    verdict = "PASS" if (
        table_exists
        and not missing
        and len(columns) == 16
        and shadow_default_ok
        and runtime_default_ok
        and execution_default_ok
        and unique_ok
    ) else "FAIL"

    print()
    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        raise SystemExit(1)

    print("RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
