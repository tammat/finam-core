from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import psycopg2

from scripts.build_profit_funnel_paper_runtime_admission_v2 import (
    main as refresh_paper_runtime_admissions,
)

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_REAL_DATA_V1"


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s);", (table,))
    return cur.fetchone()[0] is not None


def col_exists(cur, table: str, col: str) -> bool:
    schema, name = table.split(".") if "." in table else ("public", table)
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s AND column_name=%s;
        """,
        (schema, name, col),
    )
    return cur.fetchone() is not None


def first_col(cur, table: str, names: list[str]) -> str | None:
    for name in names:
        if col_exists(cur, table, name):
            return name
    return None


def scalar(cur, sql: str, params: tuple = ()) -> float:
    cur.execute(sql, params)
    value = cur.fetchone()[0]
    return 0 if value is None else value


def main() -> None:
    build_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            paper_filter = "TRUE"
            if table_exists(cur, "public.closed_trades") and col_exists(cur, "public.closed_trades", "trade_source"):
                paper_filter = "lower(coalesce(trade_source::text,'')) = 'paper'"

            closed_ts = first_col(cur, "public.closed_trades", ["closed_at", "exit_ts", "closed_ts", "updated_at", "created_at"])
            pnl_col = first_col(cur, "public.closed_trades", ["net_pnl", "pnl", "gross_pnl"])

            closed_total = int(scalar(cur, f"SELECT count(*) FROM public.closed_trades WHERE {paper_filter};"))

            if closed_ts:
                closed_today = int(scalar(cur, f"""
                    SELECT count(*)
                    FROM public.closed_trades
                    WHERE {paper_filter}
                      AND {closed_ts}::date = CURRENT_DATE;
                """))
                last_closed = scalar(cur, f"""
                    SELECT max({closed_ts})
                    FROM public.closed_trades
                    WHERE {paper_filter};
                """)
            else:
                closed_today = 0
                last_closed = None

            if pnl_col and closed_ts:
                pnl_today = scalar(cur, f"""
                    SELECT coalesce(sum({pnl_col}),0)
                    FROM public.closed_trades
                    WHERE {paper_filter}
                      AND {closed_ts}::date = CURRENT_DATE;
                """)
            else:
                pnl_today = 0

            if pnl_col:
                pnl_total = scalar(cur, f"""
                    SELECT coalesce(sum({pnl_col}),0)
                    FROM public.closed_trades
                    WHERE {paper_filter};
                """)
            else:
                pnl_total = 0

            def today_count(table: str) -> int:
                if not table_exists(cur, table):
                    return 0
                ts = first_col(cur, table, ["created_at", "ts", "event_ts", "signal_ts", "fill_ts", "bar_ts", "updated_at"])
                if not ts:
                    return int(scalar(cur, f"SELECT count(*) FROM {table};"))
                return int(scalar(cur, f"SELECT count(*) FROM {table} WHERE {ts}::date = CURRENT_DATE;"))

            signals_today = today_count("public.signals")
            fills_today = today_count("public.fills")
            signal_fills_today = today_count("public.signal_fills")

            active_symbols = 0
            if table_exists(cur, "public.runtime_active_universe"):
                active_symbols = int(scalar(cur, "SELECT count(*) FROM public.runtime_active_universe;"))

            paper_status = "READY" if closed_total >= 0 else "UNKNOWN"

            cur.execute(
                """
                INSERT INTO marketcore_ui.paper_runtime_summary_v1 (
                    id, paper_status, closed_trades_total, closed_trades_today,
                    signals_today, fills_today, signal_fills_today,
                    active_symbols, pnl_today, pnl_total, last_closed_trade_at,
                    refreshed_at, source_version, build_id
                )
                VALUES (1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    paper_status=EXCLUDED.paper_status,
                    closed_trades_total=EXCLUDED.closed_trades_total,
                    closed_trades_today=EXCLUDED.closed_trades_today,
                    signals_today=EXCLUDED.signals_today,
                    fills_today=EXCLUDED.fills_today,
                    signal_fills_today=EXCLUDED.signal_fills_today,
                    active_symbols=EXCLUDED.active_symbols,
                    pnl_today=EXCLUDED.pnl_today,
                    pnl_total=EXCLUDED.pnl_total,
                    last_closed_trade_at=EXCLUDED.last_closed_trade_at,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
                """,
                (
                    paper_status,
                    closed_total,
                    closed_today,
                    signals_today,
                    fills_today,
                    signal_fills_today,
                    active_symbols,
                    pnl_today,
                    pnl_total,
                    last_closed,
                    now,
                    SOURCE_VERSION,
                    build_id,
                ),
            )

    print("PAPER_RUNTIME_REAL_DATA_V1_BUILT")
    print(f"build_id={build_id}")
    refresh_paper_runtime_admissions()


if __name__ == "__main__":
    main()
