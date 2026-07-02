from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class DailyCenterRepository:
    def load(self) -> dict:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT day_status, capital_status, research_status, risk_status,
                           runtime_status, next_action, decision_hint
                    FROM marketcore_ui.daily_center_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.daily_center_summary_v1 is empty")

        return {
            "day_status": str(row[0]),
            "capital_status": str(row[1]),
            "research_status": str(row[2]),
            "risk_status": str(row[3]),
            "runtime_status": str(row[4]),
            "next_action": str(row[5]),
            "decision_hint": str(row[6]),
            "data_source": "marketcore_ui.daily_center_summary_v1",
        }
