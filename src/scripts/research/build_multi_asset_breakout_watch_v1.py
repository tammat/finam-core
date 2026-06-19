#!/usr/bin/env python3
from __future__ import annotations

import os

import psycopg

from finam_core.strategy.instrument_profile import resolve_instrument_signal_profile


LOOKBACK_BARS = int(os.getenv("LOOKBACK_BARS", "30"))


def main() -> int:
    print("=== MULTI ASSET BREAKOUT WATCH V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"lookback_bars={LOOKBACK_BARS}")

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
                order by symbol
                """
            )
            runtime_rows = cur.fetchall()

            print()
            print("MULTI_ASSET_BREAKOUT_WATCH_ROWS")

            rows_total = 0
            breakout_ready = 0
            no_bars = 0
            no_breakout = 0
            atr_blocked = 0
            volume_blocked = 0

            for symbol, strategy, timeframe, is_enabled, score, updated_at in runtime_rows:
                profile = resolve_instrument_signal_profile(symbol, timeframe or "M5")

                cur.execute(
                    """
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                    order by ts desc
                    limit %s
                    """,
                    (symbol, profile.timeframe, LOOKBACK_BARS + 1),
                )
                raw_rows = cur.fetchall()

                if len(raw_rows) < 2:
                    no_bars += 1
                    print(
                        "MULTI_ASSET_BREAKOUT_WATCH_ROW "
                        f"symbol={symbol} asset_class={profile.asset_class} timeframe={profile.timeframe} "
                        f"status=NO_ENOUGH_BARS rows={len(raw_rows)}"
                    )
                    continue

                rows = list(reversed(raw_rows))
                latest = rows[-1]
                previous = rows[:-1]

                ts, open_, high, low, close, volume = latest

                close_f = float(close or 0.0)
                high_f = float(high or close_f)
                low_f = float(low or close_f)
                volume_f = float(volume or 0.0)

                previous_highs = [float(row[2]) for row in previous if row[2] is not None]
                previous_volumes = [float(row[5] or 0.0) for row in previous]

                prev_high = max(previous_highs) if previous_highs else None
                avg_volume = sum(previous_volumes) / len(previous_volumes) if previous_volumes else 0.0

                atr_abs = max(high_f - low_f, 0.0)
                atr_pct = atr_abs / close_f if close_f else 0.0
                volume_ratio = volume_f / avg_volume if avg_volume else 0.0

                breakout_ok = close_f > prev_high if prev_high is not None else False
                atr_ok = atr_pct >= profile.atr_min_pct

                if profile.use_volume_filter and profile.volume_mult is not None:
                    volume_ok = volume_ratio >= profile.volume_mult
                else:
                    volume_ok = True

                ready = breakout_ok and atr_ok and volume_ok

                rows_total += 1
                breakout_ready += int(ready)
                no_breakout += int(not breakout_ok)
                atr_blocked += int(not atr_ok)
                volume_blocked += int(not volume_ok)

                if ready:
                    status = "BREAKOUT_READY"
                else:
                    reasons = []
                    if not breakout_ok:
                        reasons.append("NO_BREAKOUT")
                    if not atr_ok:
                        reasons.append("ATR_TOO_LOW")
                    if not volume_ok:
                        reasons.append("VOLUME_TOO_LOW")
                    status = "|".join(reasons)

                print(
                    "MULTI_ASSET_BREAKOUT_WATCH_ROW "
                    f"symbol={symbol} strategy={strategy} asset_class={profile.asset_class} "
                    f"timeframe={profile.timeframe} ts={ts} close={close_f:.6f} "
                    f"prev_high={prev_high} breakout_ok={int(breakout_ok)} "
                    f"atr_pct={atr_pct:.8f} atr_min_pct={profile.atr_min_pct:.8f} atr_ok={int(atr_ok)} "
                    f"volume={volume_f:.2f} avg_volume={avg_volume:.2f} volume_ratio={volume_ratio:.6f} "
                    f"volume_mult={profile.volume_mult if profile.volume_mult is not None else 'None'} "
                    f"volume_ok={int(volume_ok)} status={status} score={score}"
                )

    print()
    print("MULTI_ASSET_BREAKOUT_WATCH_SUMMARY")
    print(f"rows_total={rows_total}")
    print(f"breakout_ready={breakout_ready}")
    print(f"no_bars={no_bars}")
    print(f"no_breakout={no_breakout}")
    print(f"atr_blocked={atr_blocked}")
    print(f"volume_blocked={volume_blocked}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if breakout_ready > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_WATCH_HAS_READY_SETUPS")
    elif rows_total > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_WATCH_NO_READY_SETUPS")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_WATCH_NO_EVALUATED_ROWS")

    print("MULTI_ASSET_BREAKOUT_WATCH_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
