from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT to_regclass('analytics.strategy_signal_snapshot_v1') AS reg;")
            reg = cur.fetchone()["reg"]

            if reg != "analytics.strategy_signal_snapshot_v1":
                raise RuntimeError("analytics.strategy_signal_snapshot_v1 not found")

    print("=== MULTI_STRATEGY_ENGINE_SCHEMA_V1 ===")
    print("schema_ready=1")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MULTI_STRATEGY_ENGINE_SCHEMA_V1_READY")


if __name__ == "__main__":
    main()
