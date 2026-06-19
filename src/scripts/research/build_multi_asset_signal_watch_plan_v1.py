#!/usr/bin/env python3
from __future__ import annotations

import os

import psycopg

from finam_core.strategy.instrument_profile import resolve_instrument_signal_profile


DEFAULT_SYMBOLS = [
    "SBER@MISX",
    "LKOH@MISX",
    "PLZL@MISX",
    "X5@MISX",
    "VTBR@MISX",
    "T@MISX",
    "BRN6@RTSX",
    "NGN6@RTSX",
    "IMOEX@MISX",
]


def main() -> int:
    print("=== MULTI ASSET SIGNAL WATCH PLAN V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")

    database_url = os.getenv("DATABASE_URL")
    symbols = []

    if database_url:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select symbol, strategy, timeframe, is_enabled, score, updated_at
                    from runtime_active_universe
                    where is_enabled = true
                    order by symbol
                    """
                )
                for symbol, strategy, timeframe, is_enabled, score, updated_at in cur.fetchall():
                    symbols.append((symbol, strategy, timeframe, score, updated_at, "runtime_active_universe"))

    if not symbols:
        for symbol in DEFAULT_SYMBOLS:
            symbols.append((symbol, "WATCH_ONLY", "M5", None, None, "default_watchlist"))

    print()
    print("MULTI_ASSET_SIGNAL_WATCH_PROFILE_ROWS")

    rows_total = 0
    equity_rows = 0
    futures_rows = 0
    index_rows = 0
    unknown_rows = 0

    for symbol, strategy, timeframe, score, updated_at, source in symbols:
        profile = resolve_instrument_signal_profile(symbol, timeframe or "M5")

        rows_total += 1
        if profile.asset_class == "EQUITY":
            equity_rows += 1
        elif profile.asset_class in {"BRENT_FUTURES", "GAS_FUTURES"}:
            futures_rows += 1
        elif profile.asset_class == "MOEX_INDEX":
            index_rows += 1
        else:
            unknown_rows += 1

        print(
            "MULTI_ASSET_SIGNAL_WATCH_PROFILE_ROW "
            f"symbol={symbol} strategy={strategy} source={source} "
            f"asset_class={profile.asset_class} timeframe={profile.timeframe} "
            f"atr_min_pct={profile.atr_min_pct:.6f} "
            f"volume_mult={profile.volume_mult if profile.volume_mult is not None else 'None'} "
            f"use_volume_filter={int(profile.use_volume_filter)} "
            f"breakout_lookback={profile.breakout_lookback} "
            f"score={score} updated_at={updated_at}"
        )

    print()
    print("MULTI_ASSET_SIGNAL_WATCH_PLAN_SUMMARY")
    print(f"rows_total={rows_total}")
    print(f"equity_rows={equity_rows}")
    print(f"futures_rows={futures_rows}")
    print(f"index_rows={index_rows}")
    print(f"unknown_rows={unknown_rows}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if rows_total > 0 and unknown_rows == 0:
        print("VERDICT=MULTI_ASSET_SIGNAL_WATCH_PLAN_READY")
    elif rows_total > 0:
        print("VERDICT=MULTI_ASSET_SIGNAL_WATCH_PLAN_HAS_UNKNOWN_SYMBOLS")
    else:
        print("VERDICT=MULTI_ASSET_SIGNAL_WATCH_PLAN_EMPTY")

    print("MULTI_ASSET_SIGNAL_WATCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
