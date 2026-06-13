#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_enable_package (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    admission_decision text NOT NULL,
    enable_status text NOT NULL,
    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_enable_package_symbol
ON shadow_runtime_enable_package(symbol, created_at DESC);
"""

SQL = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    admission_decision,
    admission_reason
FROM shadow_runtime_admission_board
ORDER BY symbol, id DESC;
"""

def main() -> int:
    print("=== SHADOW RUNTIME ENABLE PACKAGE V1 ===")
    print("mode=enable_package")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    enabled = 0
    not_enabled = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("ENABLE_ROWS")

            for row in rows:
                if row["admission_decision"] == "ADMIT_SHADOW_RUNTIME":
                    enable_status = "SHADOW_RUNTIME_ENABLED"
                    shadow_runtime_allowed = True
                    enabled += 1
                else:
                    enable_status = "NOT_ENABLED"
                    shadow_runtime_allowed = False
                    not_enabled += 1

                payload = {
                    "symbol": row["symbol"],
                    "source": row["source"],
                    "admission_decision": row["admission_decision"],
                    "admission_reason": row["admission_reason"],
                    "enable_status": enable_status,
                    "shadow_runtime_allowed": shadow_runtime_allowed,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_enable_package (
                        symbol,
                        source,
                        admission_decision,
                        enable_status,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,false,%s::jsonb)
                    """,
                    (
                        row["symbol"],
                        row["source"],
                        row["admission_decision"],
                        enable_status,
                        shadow_runtime_allowed,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "ENABLE_ROW "
                    f"symbol={row['symbol']} "
                    f"source={row['source']} "
                    f"admission={row['admission_decision']} "
                    f"enable_status={enable_status} "
                    f"shadow_runtime_allowed={int(shadow_runtime_allowed)} "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW enabled={enabled} not_enabled={not_enabled}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_ENABLE_PACKAGE_READY")
    print("SHADOW_RUNTIME_ENABLE_PACKAGE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
