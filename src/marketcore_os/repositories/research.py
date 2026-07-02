from __future__ import annotations

import os

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class ResearchRepository:
    def load(self) -> dict[str, int | str]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pipeline_status, top3_status, research_candidates,
                           oos_pass, paper_ready, source_version, build_id
                    FROM marketcore_ui.research_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.research_summary_v1 is empty")

        return {
            "pipeline_status": str(row[0]),
            "top3_status": str(row[1]),
            "research_candidates": int(row[2]),
            "oos_pass": int(row[3]),
            "paper_ready": int(row[4]),
            "data_source": "marketcore_ui.research_summary_v1",
            "source_version": str(row[5]),
            "build_id": str(row[6]),
        }
