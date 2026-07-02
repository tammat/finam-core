from __future__ import annotations

import os
from decimal import Decimal

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class RiskRepository:
    def load(self) -> dict[str, object]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT runtime_allowed, execution_allowed, micro_live_allowed,
                           daily_risk_pct, source_version, build_id
                    FROM marketcore_ui.risk_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.risk_summary_v1 is empty")

        return {
            "runtime_allowed": bool(row[0]),
            "execution_allowed": bool(row[1]),
            "micro_live_allowed": bool(row[2]),
            "daily_risk_pct": Decimal(str(row[3])),
            "data_source": "marketcore_ui.risk_summary_v1",
            "source_version": str(row[4]),
            "build_id": str(row[5]),
        }
