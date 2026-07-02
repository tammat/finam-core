from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2 import errors

DB = os.getenv("DATABASE_URL", "postgresql://alex@/finam_core")


class CapitalRepository:
    def load(self) -> dict[str, Decimal | str]:
        planned = Decimal(os.getenv("MARKETCORE_PLANNED_CAPITAL_RUB", "500000"))

        with psycopg2.connect(DB) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('marketcore_capital_state_v1');")
                exists = cur.fetchone()[0] is not None

                if not exists:
                    return {
                        "planned_capital": planned,
                        "working_capital": Decimal("0"),
                        "available_capital": planned,
                        "today_pnl": Decimal("0"),
                        "base_currency": "RUB",
                        "data_source": "ENV_FALLBACK",
                    }

                try:
                    cur.execute("""
                        SELECT planned_capital, working_capital, today_pnl, base_currency
                        FROM marketcore_capital_state_v1
                        WHERE id = 1;
                    """)
                    row = cur.fetchone()
                except errors.InsufficientPrivilege:
                    return {
                        "planned_capital": planned,
                        "working_capital": Decimal("0"),
                        "available_capital": planned,
                        "today_pnl": Decimal("0"),
                        "base_currency": "RUB",
                        "data_source": "NO_TABLE_PRIVILEGE_FALLBACK",
                    }

        if row is None:
            return {
                "planned_capital": planned,
                "working_capital": Decimal("0"),
                "available_capital": planned,
                "today_pnl": Decimal("0"),
                "base_currency": "RUB",
                "data_source": "EMPTY_TABLE_FALLBACK",
            }

        planned_capital = Decimal(str(row[0]))
        working_capital = Decimal(str(row[1]))
        today_pnl = Decimal(str(row[2]))

        return {
            "planned_capital": planned_capital,
            "working_capital": working_capital,
            "available_capital": planned_capital - working_capital,
            "today_pnl": today_pnl,
            "base_currency": str(row[3]),
            "data_source": "POSTGRES",
        }
