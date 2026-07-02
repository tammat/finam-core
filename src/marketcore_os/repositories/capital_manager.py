from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class CapitalManagerRepository:
    def load(self) -> dict:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT planned_capital, working_capital, available_capital,
                           exposure_pct, deployment_limit_pct, risk_mode,
                           manager_status, next_action
                    FROM marketcore_ui.capital_manager_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.capital_manager_summary_v1 is empty")

        return {
            "planned_capital": float(row[0]),
            "working_capital": float(row[1]),
            "available_capital": float(row[2]),
            "exposure_pct": float(row[3]),
            "deployment_limit_pct": float(row[4]),
            "risk_mode": str(row[5]),
            "manager_status": str(row[6]),
            "next_action": str(row[7]),
            "data_source": "marketcore_ui.capital_manager_summary_v1",
        }
