from __future__ import annotations

import os

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class ProgramRepository:
    def load(self) -> dict[str, str]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT quarter, platform_status, research_status, top3_status,
                           paper_status, marketcore_status, source_version, build_id
                    FROM marketcore_ui.program_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.program_summary_v1 is empty")

        return {
            "quarter": str(row[0]),
            "platform_status": str(row[1]),
            "research_status": str(row[2]),
            "top3_status": str(row[3]),
            "paper_status": str(row[4]),
            "marketcore_status": str(row[5]),
            "data_source": "marketcore_ui.program_summary_v1",
            "source_version": str(row[6]),
            "build_id": str(row[7]),
        }
