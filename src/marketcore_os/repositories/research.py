from __future__ import annotations

import os

import psycopg2
from psycopg2 import errors

DB = os.getenv("DATABASE_URL", "postgresql://alex@/finam_core")


class ResearchRepository:
    def _table_exists(self, table_name: str) -> bool:
        try:
            with psycopg2.connect(DB) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s);", (table_name,))
                    return cur.fetchone()[0] is not None
        except Exception:
            return False

    def _count(self, table_name: str, where_sql: str = "TRUE") -> int:
        if not self._table_exists(table_name):
            return 0
        try:
            with psycopg2.connect(DB) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(f"SELECT count(*) FROM {table_name} WHERE {where_sql};")
                    return int(cur.fetchone()[0] or 0)
        except (errors.InsufficientPrivilege, errors.UndefinedTable):
            return 0
        except Exception:
            return 0

    def load(self) -> dict[str, int | str]:
        return {
            "research_candidates": self._count(
                "analytics_global_edge_expanded_runtime_candidates_v2",
                "candidate_status='RESEARCH_CANDIDATE'",
            ),
            "oos_pass": self._count(
                "analytics_global_edge_top3_oos_validation_v1",
                "oos_status='OOS_PASS'",
            ),
            "paper_ready": self._count(
                "analytics_global_edge_top3_runtime_approval_board_v1",
                "board_decision='APPROVE_PAPER'",
            ),
            "data_source": "POSTGRES",
        }
