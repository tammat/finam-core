from __future__ import annotations

import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class ProfitRepository:
    def _table_exists(self, cur, table_name: str) -> bool:
        cur.execute("SELECT to_regclass(%s);", (table_name,))
        return cur.fetchone()[0] is not None

    def _count(self, cur, table_name: str, where_sql: str = "TRUE") -> int:
        if not self._table_exists(cur, table_name):
            return 0
        cur.execute(f"SELECT count(*) FROM {table_name} WHERE {where_sql};")
        return int(cur.fetchone()[0] or 0)

    def load(self) -> dict[str, int | str]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                production_edges = self._count(
                    cur,
                    "marketcore_production_edge_v1",
                )

                paper_edges = self._count(
                    cur,
                    "analytics_global_edge_top3_runtime_approval_board_v1",
                    "board_decision='APPROVE_PAPER'",
                )

                shadow_edges = self._count(
                    cur,
                    "analytics_global_edge_top3_shadow_runtime_execution_v1",
                    "shadow_status='SHADOW_ACTIVE'",
                )

                research_candidates = self._count(
                    cur,
                    "analytics_global_edge_expanded_runtime_candidates_v2",
                    "candidate_status='RESEARCH_CANDIDATE'",
                )

                if research_candidates == 0:
                    research_candidates = self._count(
                        cur,
                        "analytics_global_edge_runtime_candidates_v2",
                        "candidate_status='RESEARCH_CANDIDATE'",
                    )

        return {
            "production_edges": production_edges,
            "paper_edges": paper_edges,
            "shadow_edges": shadow_edges,
            "research_candidates": research_candidates,
            "data_source": "POSTGRES",
        }
