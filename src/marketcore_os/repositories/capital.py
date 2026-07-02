from __future__ import annotations

import os
from decimal import Decimal

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class CapitalRepository:
    def load(self) -> dict[str, Decimal | str]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT planned_capital, working_capital, available_capital,
                           today_pnl, source_version, build_id
                    FROM marketcore_ui.capital_summary_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("marketcore_ui.capital_summary_v1 is empty")

        return {
            "planned_capital": Decimal(str(row[0])),
            "working_capital": Decimal(str(row[1])),
            "available_capital": Decimal(str(row[2])),
            "today_pnl": Decimal(str(row[3])),
            "base_currency": "RUB",
            "data_source": "marketcore_ui.capital_summary_v1",
            "source_version": str(row[4]),
            "build_id": str(row[5]),
        }
