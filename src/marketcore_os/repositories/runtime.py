from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class RuntimeCenterRepository:
    def load(self) -> dict:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT runtime_status, paper_status, production_status, risk_status,
                           active_symbols, active_edges, active_positions,
                           signals_today, trades_today, pnl_today, next_action
                    FROM marketcore_ui.runtime_center_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.runtime_center_summary_v1 is empty")

        return {
            "runtime_status": str(row[0]),
            "paper_status": str(row[1]),
            "production_status": str(row[2]),
            "risk_status": str(row[3]),
            "active_symbols": int(row[4]),
            "active_edges": int(row[5]),
            "active_positions": int(row[6]),
            "signals_today": int(row[7]),
            "trades_today": int(row[8]),
            "pnl_today": float(row[9]),
            "next_action": str(row[10]),
            "data_source": "marketcore_ui.runtime_center_summary_v1",
        }
