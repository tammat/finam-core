#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


TARGETS = ["OZON@MISX", "SBERP@MISX", "T@MISX"]
TIMEFRAMES = ["M1", "M5", "H1"]


def source_hits() -> list[str]:
    hits: list[str] = []
    roots = [Path("src/scripts"), Path("src/finam_core")]
    needles = [
        "market_bars",
        "backfill",
        "equity",
        "candles",
        "bars",
    ]

    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8").lower()
            except UnicodeDecodeError:
                continue

            name = str(p).lower()
            score = 0
            if "backfill" in name:
                score += 2
            if "equity" in name:
                score += 2
            if "market_bars" in text:
                score += 2
            if "candles" in text or "bars" in text:
                score += 1

            if score >= 3 and any(n in text or n in name for n in needles):
                hits.append(str(p))

    return sorted(set(hits))


def main() -> int:
    print("=== EQUITY MISSING MARKET BARS BACKFILL PLAN V1 ===")
    print("mode=read_only_backfill_plan")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")
    print("db_update=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    missing = 0
    runtime_enabled = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            print()
            print("EQUITY_TARGET_ROWS")

            for symbol in TARGETS:
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
                    limit 1
                    """,
                    {"symbol": symbol},
                )
                runtime = cur.fetchone()

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
                      and timeframe = any(%(timeframes)s)
                    group by timeframe
                    order by timeframe
                    """,
                    {"symbol": symbol, "timeframes": TIMEFRAMES},
                )
                bars = cur.fetchall()

                cur.execute(
                    """
                    select
                      count(*)::int as observations,
                      count(*) filter (where status like %(ready_pattern)s)::int as ready_count,
                      max(created_at) as last_observed,
                      max(status) as last_status
                    from analytics_multi_asset_breakout_row_v1
                    where symbol = %(symbol)s
                    """,
                    {"symbol": symbol, "ready_pattern": "%BREAKOUT_READY%"},
                )
                hist = cur.fetchone()

                has_runtime = runtime is not None
                has_bars = len(bars) > 0
                runtime_enabled += int(bool(runtime and runtime["is_enabled"]))
                missing += int(not has_bars)

                verdict = "BACKFILL_REQUIRED" if has_runtime and not has_bars else "OK_OR_NOT_RUNTIME"

                print(
                    "EQUITY_BACKFILL_TARGET_ROW "
                    f"symbol={symbol} runtime={int(has_runtime)} "
                    f"runtime_enabled={int(bool(runtime and runtime['is_enabled']))} "
                    f"has_bars={int(has_bars)} observations={hist['observations']} "
                    f"ready_count={hist['ready_count']} last_observed={hist['last_observed']} "
                    f"last_status={hist['last_status']} verdict={verdict}"
                )

                if runtime:
                    print(
                        "RUNTIME_ROW "
                        f"symbol={symbol} strategy={runtime['strategy']} timeframe={runtime['timeframe']} "
                        f"score={runtime['score']} source={runtime['source']} "
                        f"updated_at={runtime['updated_at']} last_seen_at={runtime['last_seen_at']}"
                    )

                for b in bars:
                    print(
                        "BARS_ROW "
                        f"symbol={symbol} timeframe={b['timeframe']} bars={b['bars']} "
                        f"first_ts={b['first_ts']} last_ts={b['last_ts']} age={b['age']}"
                    )

    print()
    print("BACKFILL_SCRIPT_CANDIDATES")
    hits = source_hits()
    if not hits:
        print("BACKFILL_SCRIPT_ROW status=NO_EXISTING_BACKFILL_SCRIPT_FOUND")
    else:
        for h in hits[:40]:
            print(f"BACKFILL_SCRIPT_ROW path={h}")

    print()
    print("EQUITY_BACKFILL_PLAN_SUMMARY")
    print(f"targets_total={len(TARGETS)}")
    print(f"runtime_enabled={runtime_enabled}")
    print(f"missing_market_bars={missing}")
    print(f"candidate_scripts={len(hits)}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if missing > 0:
        print("VERDICT=EQUITY_MISSING_MARKET_BARS_BACKFILL_PLAN_REQUIRED")
    else:
        print("VERDICT=EQUITY_MISSING_MARKET_BARS_BACKFILL_NOT_REQUIRED")

    print("EQUITY_MISSING_MARKET_BARS_BACKFILL_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
