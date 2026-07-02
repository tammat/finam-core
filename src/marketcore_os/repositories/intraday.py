from __future__ import annotations
import os
import psycopg2

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")

class IntradayRepository:

    def load(self):

        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT
                    runtime_allowed,
                    execution_allowed,
                    micro_live_allowed
                FROM marketcore_ui.risk_summary_v1
                WHERE id=1
                """)

                risk=cur.fetchone()

                cur.execute("""
                SELECT
                    paper_positions,
                    production_positions,
                    exposure_pct
                FROM marketcore_ui.portfolio_summary_v1
                WHERE id=1
                """)

                p=cur.fetchone()

                cur.execute("""
                SELECT
                    research_candidates,
                    paper_ready
                FROM marketcore_ui.research_summary_v1
                WHERE id=1
                """)

                r=cur.fetchone()

        return {

            "runtime_status":"ON" if risk[0] else "OFF",
            "paper_status":"READY",
            "production_status":"ON" if risk[1] else "OFF",

            "active_symbols":int(r[0]),
            "active_edges":int(r[1]),
            "active_positions":int(p[0])+int(p[1]),
            "exposure_pct":float(p[2]),

            "next_action":"MARKETCORE_CAPITAL_MANAGER_V1",

            "data_source":"marketcore_ui"

        }
