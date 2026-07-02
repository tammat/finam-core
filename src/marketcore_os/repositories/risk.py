from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2 import errors

DB = os.getenv("DATABASE_URL", "postgresql://alex@/finam_core")


class RiskRepository:
    def _table_exists(self, table_name: str) -> bool:
        try:
            with psycopg2.connect(DB) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s);", (table_name,))
                    return cur.fetchone()[0] is not None
        except Exception:
            return False

    def _count_allowed(self, table_name: str) -> int:
        if not self._table_exists(table_name):
            return 0

        try:
            with psycopg2.connect(DB) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT count(*)
                        FROM {table_name}
                        WHERE COALESCE(runtime_allowed,false)=true
                           OR COALESCE(execution_allowed,false)=true
                           OR COALESCE(micro_live_allowed,false)=true;
                    """)
                    return int(cur.fetchone()[0] or 0)
        except (errors.InsufficientPrivilege, errors.UndefinedTable, errors.UndefinedColumn):
            return 0
        except Exception:
            return 0

    def load(self) -> dict[str, object]:
        expanded_allowed = self._count_allowed(
            "analytics_global_edge_expanded_runtime_candidates_v2"
        )
        base_allowed = self._count_allowed(
            "analytics_global_edge_runtime_candidates_v2"
        )

        any_allowed = expanded_allowed + base_allowed

        return {
            "runtime_allowed": any_allowed > 0,
            "execution_allowed": False,
            "micro_live_allowed": False,
            "daily_risk_pct": Decimal("0.00"),
            "data_source": "POSTGRES",
        }
