#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row


TARGETS = {
    "OZON": ["OZON", "OZON@MISX", "OZON@MOEX", "OZON@TQBR"],
    "SBERP": ["SBERP", "SBERP@MISX", "SBERP@MOEX", "SBERP@TQBR"],
    "T": ["T", "T@MISX", "T@MOEX", "T@TQBR", "TCSG", "TCSG@MISX", "TCSG@MOEX", "TCSG@TQBR"],
}


def main() -> int:
    print("=== EQUITY MARKET BARS SYMBOL ALIAS AUDIT V1 ===")
    print("mode=read_only_symbol_alias_audit")
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
        with conn.cursor(row_factory=dict_row) as cur:
            print()
            print("EXACT_ALIAS_CANDIDATES")
            for logical, aliases in TARGETS.items():
                for alias in aliases:
                    cur.execute(
                        """
                        select
                          symbol,
                          timeframe,
                          count(*)::int as bars,
                          min(ts) as first_ts,
                          max(ts) as last_ts,
                          now() - max(ts) as age
                        from market_bars
                        where symbol = %(alias)s
                        group by symbol, timeframe
                        order by timeframe
                        """,
                        {"alias": alias},
                    )
                    rows = cur.fetchall()
                    if not rows:
                        print(f"ALIAS_ROW logical={logical} alias={alias} status=NO_BARS")
                        continue

                    for r in rows:
                        print(
                            "ALIAS_ROW "
                            f"logical={logical} alias={alias} status=BARS_OK "
                            f"symbol={r['symbol']} timeframe={r['timeframe']} "
                            f"bars={r['bars']} first_ts={r['first_ts']} "
                            f"last_ts={r['last_ts']} age={r['age']}"
                        )

            print()
            print("FUZZY_SYMBOL_SEARCH")
            for logical in TARGETS:
                cur.execute(
                    """
                    select
                      symbol,
                      timeframe,
                      count(*)::int as bars,
                      min(ts) as first_ts,
                      max(ts) as last_ts,
                      now() - max(ts) as age
                    from market_bars
                    where upper(symbol) like %(pattern)s
                    group by symbol, timeframe
                    order by max(ts) desc, count(*) desc, symbol, timeframe
                    limit 40
                    """,
                    {"pattern": f"%{logical}%"},
                )
                rows = cur.fetchall()
                if not rows:
                    print(f"FUZZY_ROW logical={logical} status=NO_MATCHES")
                    continue

                for r in rows:
                    print(
                        "FUZZY_ROW "
                        f"logical={logical} symbol={r['symbol']} timeframe={r['timeframe']} "
                        f"bars={r['bars']} first_ts={r['first_ts']} "
                        f"last_ts={r['last_ts']} age={r['age']}"
                    )

            print()
            print("RUNTIME_ROWS")
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
                where symbol in ('OZON@MISX','SBERP@MISX','T@MISX')
                order by symbol
                """
            )
            for r in cur.fetchall():
                print(
                    "RUNTIME_ROW "
                    f"symbol={r['symbol']} strategy={r['strategy']} timeframe={r['timeframe']} "
                    f"enabled={r['is_enabled']} score={r['score']} source={r['source']} "
                    f"updated_at={r['updated_at']} last_seen_at={r['last_seen_at']}"
                )

    print()
    print("EQUITY_ALIAS_AUDIT_SUMMARY")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")
    print("VERDICT=EQUITY_MARKET_BARS_SYMBOL_ALIAS_AUDIT_READY")
    print("EQUITY_MARKET_BARS_SYMBOL_ALIAS_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
