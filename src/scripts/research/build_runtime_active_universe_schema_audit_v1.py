#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


COLUMNS_SQL = """
select
    column_name,
    data_type,
    is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'runtime_active_universe'
order by ordinal_position;
"""


ROWS_SQL = """
select *
from runtime_active_universe
order by priority desc nulls last, score desc nulls last, symbol
limit 50;
"""


TRADE_DATES_SQL = """
select
    created_at::date as trade_date,
    count(*) as trades,
    count(*) filter (where strategy is null or strategy = '') as strategy_missing,
    count(*) filter (where timeframe is null or timeframe = '') as timeframe_missing,
    count(*) filter (where continuous_symbol is null or continuous_symbol = '') as continuous_symbol_missing,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
group by created_at::date
order by trade_date desc
limit 10;
"""


def fmt_row(row: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in row.items())


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== RUNTIME ACTIVE UNIVERSE SCHEMA AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(COLUMNS_SQL)
            columns = cur.fetchall()

            print()
            print("RUNTIME_ACTIVE_UNIVERSE_COLUMNS")
            for row in columns:
                print(
                    "RUNTIME_COLUMN "
                    f"name={row['column_name']} "
                    f"type={row['data_type']} "
                    f"nullable={row['is_nullable']}"
                )

            cur.execute(ROWS_SQL)
            rows = cur.fetchall()

            print()
            print("RUNTIME_ACTIVE_UNIVERSE_ROWS")
            for row in rows:
                print("RUNTIME_ROW " + fmt_row(dict(row)))

            cur.execute(TRADE_DATES_SQL)
            trade_dates = cur.fetchall()

            print()
            print("TRADE_DATES_RECENT")
            for row in trade_dates:
                print(
                    "TRADE_DATE_ROW "
                    f"trade_date={row['trade_date']} "
                    f"trades={row['trades']} "
                    f"strategy_missing={row['strategy_missing']} "
                    f"timeframe_missing={row['timeframe_missing']} "
                    f"continuous_symbol_missing={row['continuous_symbol_missing']} "
                    f"first_trade={row['first_trade']} "
                    f"last_trade={row['last_trade']}"
                )

    print()
    print("VERDICT=RUNTIME_ACTIVE_UNIVERSE_SCHEMA_AUDIT_READY")
    print("RUNTIME_ACTIVE_UNIVERSE_SCHEMA_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
