from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM marketcore_ui.paper_runtime_equity_curve_v1;")
            cur.execute("DELETE FROM marketcore_ui.paper_runtime_drawdown_curve_v1;")

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_equity_curve_v1 (
                    point_no, ts, ticker, source, realized_pnl, equity_pnl, refreshed_at
                )
                SELECT
                    row_number() OVER (ORDER BY ts)::int AS point_no,
                    ts,
                    "Тикер"::text AS ticker,
                    "Источник"::text AS source,
                    "Realized P&L"::numeric AS realized_pnl,
                    "Equity P&L"::numeric AS equity_pnl,
                    now()
                FROM public.v_trades_equity_curve_ui
                WHERE "Источник" = 'paper'
                ORDER BY ts;
            """)

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_drawdown_curve_v1 (
                    point_no, ts, ticker, source, equity_pnl,
                    peak_equity_pnl, drawdown, drawdown_pct, refreshed_at
                )
                SELECT
                    row_number() OVER (ORDER BY ts)::int AS point_no,
                    ts,
                    "Тикер"::text AS ticker,
                    "Источник"::text AS source,
                    "Equity P&L"::numeric AS equity_pnl,
                    "Peak Equity P&L"::numeric AS peak_equity_pnl,
                    "Drawdown"::numeric AS drawdown,
                    "Drawdown %"::numeric AS drawdown_pct,
                    now()
                FROM public.v_trades_drawdown_curve_ui
                WHERE "Источник" = 'paper'
                ORDER BY ts;
            """)

    print("PAPER_RUNTIME_EQUITY_CURVE_V1_BUILT")


if __name__ == "__main__":
    main()
