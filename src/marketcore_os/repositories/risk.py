from __future__ import annotations

import os
from decimal import Decimal

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class RiskRepository:
    def _table_exists(self, cur, table_name: str) -> bool:
        cur.execute("SELECT to_regclass(%s);", (table_name,))
        return cur.fetchone()[0] is not None

    def _count_allowed(self, cur, table_name: str) -> int:
        if not self._table_exists(cur, table_name):
            return 0
        cur.execute(f"""
            SELECT count(*)
            FROM {table_name}
            WHERE COALESCE(runtime_allowed,false)=true
               OR COALESCE(execution_allowed,false)=true
               OR COALESCE(micro_live_allowed,false)=true;
        """)
        return int(cur.fetchone()[0] or 0)

    def load(self) -> dict[str, object]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                expanded_allowed = self._count_allowed(
                    cur,
                    "analytics_global_edge_expanded_runtime_candidates_v2",
                )
                base_allowed = self._count_allowed(
                    cur,
                    "analytics_global_edge_runtime_candidates_v2",
                )

        any_allowed = expanded_allowed + base_allowed

        return {
            "runtime_allowed": any_allowed > 0,
            "execution_allowed": False,
            "micro_live_allowed": False,
            "daily_risk_pct": Decimal("0.00"),
            "data_source": "POSTGRES",
        }
