from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class CapitalRepository:
    def load(self) -> dict[str, Decimal | str]:
        planned = Decimal(os.getenv("MARKETCORE_PLANNED_CAPITAL_RUB", "500000"))

        with psycopg2.connect(DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS marketcore_capital_state_v1 (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        planned_capital NUMERIC NOT NULL DEFAULT 500000,
                        working_capital NUMERIC NOT NULL DEFAULT 0,
                        today_pnl NUMERIC NOT NULL DEFAULT 0,
                        base_currency TEXT NOT NULL DEFAULT 'RUB',
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        CONSTRAINT marketcore_capital_state_singleton CHECK (id = 1)
                    );
                """)

                cur.execute("""
                    INSERT INTO marketcore_capital_state_v1 (id, planned_capital)
                    VALUES (1, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (planned,))

                cur.execute("""
                    SELECT planned_capital, working_capital, today_pnl, base_currency
                    FROM marketcore_capital_state_v1
                    WHERE id = 1;
                """)
                row = cur.fetchone()

        planned_capital = Decimal(str(row[0]))
        working_capital = Decimal(str(row[1]))
        today_pnl = Decimal(str(row[2]))
        base_currency = str(row[3])

        return {
            "planned_capital": planned_capital,
            "working_capital": working_capital,
            "available_capital": planned_capital - working_capital,
            "today_pnl": today_pnl,
            "base_currency": base_currency,
            "data_source": "POSTGRES",
        }
