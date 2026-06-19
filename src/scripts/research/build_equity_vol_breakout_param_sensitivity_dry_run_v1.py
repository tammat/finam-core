#!/usr/bin/env python3
from __future__ import annotations

import os
from itertools import product

import psycopg


ACTIVE_SINCE_UTC = os.getenv("ACTIVE_SINCE_UTC", "2026-06-19 07:24:35+00")
TIMEFRAME = os.getenv("TIMEFRAME", "M5")
LOOKBACK_BARS = int(os.getenv("LOOKBACK_BARS", "30"))

ATR_GRID = [float(x) for x in os.getenv("ATR_GRID", "0.0005,0.0008,0.0010,0.0015,0.0020,0.0080").split(",")]
VOLUME_GRID = [float(x) for x in os.getenv("VOLUME_GRID", "1.0,1.2,1.5").split(",")]


def main() -> int:
    print("=== EQUITY VOL BREAKOUT PARAM SENSITIVITY DRY RUN V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"active_since_utc={ACTIVE_SINCE_UTC}")
    print(f"timeframe={TIMEFRAME}")
    print(f"lookback_bars={LOOKBACK_BARS}")
    print(f"atr_grid={','.join(str(x) for x in ATR_GRID)}")
    print(f"volume_grid={','.join(str(x) for x in VOLUME_GRID)}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select symbol, strategy, timeframe, is_enabled, score, updated_at
                from runtime_active_universe
                where is_enabled = true
                  and symbol like %s
                  and strategy = 'VOLATILITY_BREAKOUT_EQUITY'
                order by symbol
                """,
                ("%@MISX",),
            )
            runtime_rows = cur.fetchall()

            print()
            print("EQUITY_VOL_BREAKOUT_SENSITIVITY_RUNTIME_ROWS")
            for row in runtime_rows:
                print(
                    "EQUITY_VOL_BREAKOUT_SENSITIVITY_RUNTIME_ROW "
                    f"symbol={row[0]} strategy={row[1]} timeframe={row[2]} "
                    f"is_enabled={int(bool(row[3]))} score={row[4]} updated_at={row[5]}"
                )

            evaluated_rows = []

            for runtime_row in runtime_rows:
                symbol = runtime_row[0]

                cur.execute(
                    """
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                      and ts <= %s::timestamptz
                    order by ts desc
                    limit %s
                    """,
                    (symbol, TIMEFRAME, ACTIVE_SINCE_UTC, LOOKBACK_BARS),
                )
                history = list(reversed(cur.fetchall()))

                cur.execute(
                    """
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                      and ts > %s::timestamptz
                    order by ts asc
                    limit 50
                    """,
                    (symbol, TIMEFRAME, ACTIVE_SINCE_UTC),
                )
                fresh_rows = cur.fetchall()

                if not fresh_rows:
                    print(
                        "EQUITY_VOL_BREAKOUT_SENSITIVITY_SOURCE_ROW "
                        f"symbol={symbol} status=NO_FRESH_BARS_AFTER_RESTART"
                    )
                    continue

                rolling = history[:]

                for ts, open_, high, low, close, volume in fresh_rows:
                    previous = rolling[-LOOKBACK_BARS:] if rolling else []
                    previous_highs = [float(row[2]) for row in previous if row[2] is not None]
                    previous_volumes = [float(row[5] or 0.0) for row in previous]

                    close_f = float(close or 0.0)
                    high_f = float(high or close_f)
                    low_f = float(low or close_f)
                    volume_f = float(volume or 0.0)

                    atr_abs = max(high_f - low_f, 0.0)
                    atr_pct = atr_abs / close_f if close_f else 0.0
                    prev_high = max(previous_highs) if previous_highs else None
                    avg_volume = (
                        sum(previous_volumes) / len(previous_volumes)
                        if previous_volumes
                        else 0.0
                    )
                    volume_ratio = volume_f / avg_volume if avg_volume else 0.0
                    breakout_ok = close_f > prev_high if prev_high is not None else False

                    evaluated_rows.append(
                        {
                            "symbol": symbol,
                            "ts": ts,
                            "close": close_f,
                            "atr_pct": atr_pct,
                            "volume": volume_f,
                            "avg_volume": avg_volume,
                            "volume_ratio": volume_ratio,
                            "prev_high": prev_high,
                            "breakout_ok": breakout_ok,
                        }
                    )

                    print(
                        "EQUITY_VOL_BREAKOUT_SENSITIVITY_SOURCE_ROW "
                        f"symbol={symbol} ts={ts} close={close_f:.6f} "
                        f"atr_pct={atr_pct:.8f} volume_ratio={volume_ratio:.6f} "
                        f"prev_high={prev_high} breakout_ok={int(breakout_ok)}"
                    )

                    rolling.append((ts, open_, high, low, close, volume))

    print()
    print("EQUITY_VOL_BREAKOUT_SENSITIVITY_GRID_ROWS")

    best_rows = []
    for atr_threshold, volume_mult in product(ATR_GRID, VOLUME_GRID):
        atr_pass = 0
        volume_pass = 0
        breakout_pass = 0
        all_pass = 0

        for row in evaluated_rows:
            atr_ok = row["atr_pct"] >= atr_threshold
            volume_ok = row["volume_ratio"] >= volume_mult
            breakout_ok = bool(row["breakout_ok"])

            atr_pass += int(atr_ok)
            volume_pass += int(volume_ok)
            breakout_pass += int(breakout_ok)
            all_pass += int(atr_ok and volume_ok and breakout_ok)

        best_rows.append((all_pass, atr_pass, volume_pass, breakout_pass, atr_threshold, volume_mult))

        print(
            "EQUITY_VOL_BREAKOUT_SENSITIVITY_GRID_ROW "
            f"atr_threshold={atr_threshold:.8f} volume_mult={volume_mult:.4f} "
            f"rows_total={len(evaluated_rows)} atr_pass={atr_pass} "
            f"volume_pass={volume_pass} breakout_pass={breakout_pass} all_pass={all_pass}"
        )

    best_rows.sort(reverse=True)
    best = best_rows[0] if best_rows else (0, 0, 0, 0, 0.0, 0.0)

    print()
    print("EQUITY_VOL_BREAKOUT_PARAM_SENSITIVITY_DRY_RUN_SUMMARY")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"evaluated_rows={len(evaluated_rows)}")
    print(f"best_all_pass={best[0]}")
    print(f"best_atr_pass={best[1]}")
    print(f"best_volume_pass={best[2]}")
    print(f"best_breakout_pass={best[3]}")
    print(f"best_atr_threshold={best[4]:.8f}")
    print(f"best_volume_mult={best[5]:.4f}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not evaluated_rows:
        print("VERDICT=EQUITY_VOL_BREAKOUT_SENSITIVITY_NO_ROWS")
    elif best[0] > 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_SENSITIVITY_HAS_PROXY_CANDIDATES")
    elif best[3] == 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_SENSITIVITY_NO_BREAKOUT_ANY_PARAMS")
    elif best[2] == 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_SENSITIVITY_VOLUME_BLOCKS_ALL")
    elif best[1] == 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_SENSITIVITY_ATR_BLOCKS_ALL")
    else:
        print("VERDICT=EQUITY_VOL_BREAKOUT_SENSITIVITY_NO_FULL_PASS")

    print("EQUITY_VOL_BREAKOUT_PARAM_SENSITIVITY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
