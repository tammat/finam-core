#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row


SYMBOLS = ["OZON@MISX", "SBERP@MISX", "T@MISX"]


def table_exists(conn: psycopg.Connection, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("select to_regclass(%s)", (name,))
        return cur.fetchone()[0] is not None


def main() -> int:
    print("=== EQUITY WATCH DATA QUALITY AUDIT V1 ===")
    print("mode=read_only_equity_data_quality")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        has_runtime = table_exists(conn, "runtime_active_universe")
        has_bars = table_exists(conn, "market_bars")
        has_rows = table_exists(conn, "analytics_multi_asset_breakout_row_v1")

        print()
        print("TABLES")
        print(f"runtime_active_universe={int(has_runtime)}")
        print(f"market_bars={int(has_bars)}")
        print(f"analytics_multi_asset_breakout_row_v1={int(has_rows)}")

        print()
        print("EQUITY_DATA_QUALITY_ROWS")

        with conn.cursor(row_factory=dict_row) as cur:
            for symbol in SYMBOLS:
                runtime_rows = []
                if has_runtime:
                    cur.execute(
                        """
                        select
                          symbol,
                          strategy,
                          timeframe,
                          is_enabled,
                          score,
                          source,
                          updated_at,
                          last_seen_at
                        from runtime_active_universe
                        where symbol = %(symbol)s
                        order by updated_at desc nulls last
                        limit 5
                        """,
                        {"symbol": symbol},
                    )
                    runtime_rows = cur.fetchall()

                bars = []
                if has_bars:
                    cur.execute(
                        """
                        select
                          timeframe,
                          count(*)::int as bars,
                          min(ts) as first_ts,
                          max(ts) as last_ts,
                          now() - max(ts) as age
                        from market_bars
                        where symbol = %(symbol)s
                          and timeframe in ('M1','M5','H1')
                        group by timeframe
                        order by timeframe
                        """,
                        {"symbol": symbol},
                    )
                    bars = cur.fetchall()

                hist = []
                if has_rows:
                    cur.execute(
                        """
                        select
                          timeframe,
                          role,
                          count(*)::int as observations,
                          count(*) filter (where status like %(ready_pattern)s)::int as ready_count,
                          max(created_at) as last_seen
                        from analytics_multi_asset_breakout_row_v1
                        where symbol = %(symbol)s
                        group by timeframe, role
                        order by observations desc, timeframe, role
                        """,
                        {"symbol": symbol, "ready_pattern": "%BREAKOUT_READY%"},
                    )
                    hist = cur.fetchall()

                latest_status = None
                if has_rows:
                    cur.execute(
                        """
                        select
                          created_at,
                          timeframe,
                          role,
                          close,
                          prev_high,
                          atr_ok,
                          volume_ok,
                          breakout_ok,
                          status
                        from analytics_multi_asset_breakout_row_v1
                        where symbol = %(symbol)s
                        order by created_at desc
                        limit 1
                        """,
                        {"symbol": symbol},
                    )
                    latest_status = cur.fetchone()

                runtime_state = "IN_RUNTIME" if runtime_rows else "NOT_IN_RUNTIME"
                bars_state = "HAS_BARS" if bars else "NO_BARS"
                hist_state = "OBSERVED" if hist else "NOT_OBSERVED"

                ready_total = sum(int(r["ready_count"] or 0) for r in hist)
                observations_total = sum(int(r["observations"] or 0) for r in hist)

                if not bars:
                    verdict = "NO_BARS"
                elif not runtime_rows:
                    verdict = "HAS_BARS_NOT_IN_RUNTIME"
                elif not hist:
                    verdict = "IN_RUNTIME_NOT_OBSERVED"
                elif ready_total == 0:
                    verdict = "OBSERVED_NO_READY"
                else:
                    verdict = "HAS_READY"

                print(
                    "EQUITY_DATA_ROW "
                    f"symbol={symbol} runtime_state={runtime_state} "
                    f"bars_state={bars_state} hist_state={hist_state} "
                    f"observations_total={observations_total} ready_total={ready_total} "
                    f"verdict={verdict}"
                )

                for r in runtime_rows:
                    print(
                        "RUNTIME_ROW "
                        f"symbol={symbol} strategy={r.get('strategy')} timeframe={r.get('timeframe')} "
                        f"enabled={r.get('is_enabled')} score={r.get('score')} "
                        f"source={r.get('source')} updated_at={r.get('updated_at')} "
                        f"last_seen_at={r.get('last_seen_at')}"
                    )

                for b in bars:
                    print(
                        "BARS_ROW "
                        f"symbol={symbol} timeframe={b['timeframe']} bars={b['bars']} "
                        f"first_ts={b['first_ts']} last_ts={b['last_ts']} age={b['age']}"
                    )

                for h in hist:
                    print(
                        "HISTORY_ROW "
                        f"symbol={symbol} timeframe={h['timeframe']} role={h['role']} "
                        f"observations={h['observations']} ready_count={h['ready_count']} "
                        f"last_seen={h['last_seen']}"
                    )

                if latest_status:
                    print(
                        "LATEST_STATUS_ROW "
                        f"symbol={symbol} created_at={latest_status['created_at']} "
                        f"timeframe={latest_status['timeframe']} role={latest_status['role']} "
                        f"close={latest_status['close']} prev_high={latest_status['prev_high']} "
                        f"breakout_ok={latest_status['breakout_ok']} atr_ok={latest_status['atr_ok']} "
                        f"volume_ok={latest_status['volume_ok']} status={latest_status['status']}"
                    )

    print()
    print("EQUITY_WATCH_DATA_QUALITY_SUMMARY")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print("VERDICT=EQUITY_WATCH_DATA_QUALITY_AUDIT_READY")
    print("EQUITY_WATCH_DATA_QUALITY_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
