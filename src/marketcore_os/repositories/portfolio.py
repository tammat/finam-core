from __future__ import annotations
import os
import psycopg2

DB = os.getenv("DATABASE_URL","postgresql:///finam_core")

class PortfolioRepository:

    def load(self):

        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        planned_capital,
                        working_capital,
                        available_capital,
                        today_pnl,
                        open_positions,
                        paper_positions,
                        production_positions,
                        exposure_pct,
                        portfolio_status,
                        next_action
                    FROM marketcore_ui.portfolio_summary_v1
                    WHERE id=1
                """)

                r = cur.fetchone()

        return {
            "planned_capital": float(r[0]),
            "working_capital": float(r[1]),
            "available_capital": float(r[2]),
            "today_pnl": float(r[3]),
            "open_positions": int(r[4]),
            "paper_positions": int(r[5]),
            "production_positions": int(r[6]),
            "exposure_pct": float(r[7]),
            "portfolio_status": str(r[8]),
            "next_action": str(r[9]),
            "data_source":"marketcore_ui.portfolio_summary_v1"
        }
