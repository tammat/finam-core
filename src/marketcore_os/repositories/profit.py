from __future__ import annotations

import os

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class ProfitRepository:
    def load(self) -> dict[str, int | str]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT production_edges, paper_edges, shadow_edges,
                           research_candidates, source_version, build_id
                    FROM marketcore_ui.profit_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.profit_summary_v1 is empty")

        return {
            "production_edges": int(row[0]),
            "paper_edges": int(row[1]),
            "shadow_edges": int(row[2]),
            "research_candidates": int(row[3]),
            "data_source": "marketcore_ui.profit_summary_v1",
            "source_version": str(row[4]),
            "build_id": str(row[5]),
        }
