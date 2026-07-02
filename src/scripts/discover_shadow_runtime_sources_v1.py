from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

PATTERNS = [
    "%shadow%",
    "%paper%",
    "%runtime%",
    "%observation%",
    "%execution%",
]

def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== SHADOW_RUNTIME_SOURCE_DISCOVERY_V1 ===")

            for pattern in PATTERNS:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog','information_schema')
                      AND table_name ILIKE %s
                    ORDER BY table_schema, table_name;
                """, (pattern,))

                rows = cur.fetchall()
                print(f"\nPATTERN={pattern} TABLES={len(rows)}")

                for schema, table in rows:
                    full = f"{schema}.{table}"
                    try:
                        cur.execute(f"SELECT count(*) FROM {full};")
                        count = cur.fetchone()[0]
                    except Exception as e:
                        conn.rollback()
                        count = f"ERROR:{type(e).__name__}"

                    print(f"TABLE {full} rows={count}")

            print("\nVERDICT=SHADOW_RUNTIME_SOURCE_DISCOVERY_V1_READY")

if __name__ == "__main__":
    main()
