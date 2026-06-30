#!/usr/bin/env python3
# Русский комментарий: read-only исследование параметров VOLATILITY_BREAKOUT_EQUITY без изменения runtime и БД.

import os
import psycopg2
from decimal import Decimal

DATABASE_URL = os.getenv("DATABASE_URL")

ATR_GRID = [Decimal("0.0005"), Decimal("0.0008"), Decimal("0.0010"), Decimal("0.0015")]
VOLUME_GRID = [Decimal("1.0"), Decimal("1.2"), Decimal("1.5")]
HORIZONS = [3, 5, 10, 15]


def main() -> int:
    print("=== EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")

    if not DATABASE_URL:
        print("VERDICT=DATABASE_URL_MISSING")
        return 1

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                select symbol
                from runtime_active_universe
                where strategy = 'VOLATILITY_BREAKOUT_EQUITY'
                  and timeframe = 'M5'
                  and is_enabled = true
                order by symbol
            """)
            symbols = [r[0] for r in cur.fetchall()]

            print(f"runtime_symbols={len(symbols)}")

            if not symbols:
                print("VERDICT=EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_NO_RUNTIME_SYMBOLS")
                return 0

            cur.execute("""
                with base as (
                    select
                        symbol,
                        ts,
                        close,
                        high,
                        volume,
                        lag(close) over (partition by symbol order by ts) as prev_close,
                        lead(close, 3) over (partition by symbol order by ts) as close_fwd_3,
                        lead(close, 5) over (partition by symbol order by ts) as close_fwd_5,
                        lead(close, 10) over (partition by symbol order by ts) as close_fwd_10,
                        lead(close, 15) over (partition by symbol order by ts) as close_fwd_15
                    from market_bars
                    where symbol = any(%s)
                      and timeframe = 'M5'
                ),
                bars as (
                    select
                        symbol,
                        ts,
                        close,
                        high,
                        volume,
                        close_fwd_3,
                        close_fwd_5,
                        close_fwd_10,
                        close_fwd_15,
                        max(high) over (
                            partition by symbol
                            order by ts
                            rows between 30 preceding and 1 preceding
                        ) as prev_high,
                        avg(volume) over (
                            partition by symbol
                            order by ts
                            rows between 30 preceding and 1 preceding
                        ) as avg_volume,
                        avg(abs(close - prev_close)) over (
                            partition by symbol
                            order by ts
                            rows between 14 preceding and current row
                        ) as atr_proxy
                    from base
                )
                select
                    symbol,
                    ts,
                    close,
                    prev_high,
                    volume,
                    avg_volume,
                    atr_proxy,
                    close_fwd_3,
                    close_fwd_5,
                    close_fwd_10,
                    close_fwd_15
                from bars
                where prev_high is not null
                  and avg_volume is not null
                  and atr_proxy is not null
                  and close_fwd_15 is not null
                order by symbol, ts
            """, (symbols,))

            rows = cur.fetchall()

        print(f"evaluated_rows={len(rows)}")

        best = None

        for atr_th in ATR_GRID:
            for vol_mult in VOLUME_GRID:
                signals = []
                for row in rows:
                    symbol, ts, close, prev_high, volume, avg_volume, atr_proxy, f3, f5, f10, f15 = row

                    close = Decimal(str(close))
                    prev_high = Decimal(str(prev_high))
                    volume = Decimal(str(volume or 0))
                    avg_volume = Decimal(str(avg_volume or 0))
                    atr_proxy = Decimal(str(atr_proxy or 0))

                    if close <= 0 or avg_volume <= 0:
                        continue

                    atr_pct = atr_proxy / close
                    volume_ratio = volume / avg_volume
                    breakout_ok = close > prev_high

                    if atr_pct >= atr_th and volume_ratio >= vol_mult and breakout_ok:
                        fwd = {
                            3: Decimal(str(f3)),
                            5: Decimal(str(f5)),
                            10: Decimal(str(f10)),
                            15: Decimal(str(f15)),
                        }
                        signals.append((symbol, close, fwd))

                result = {
                    "atr": atr_th,
                    "vol": vol_mult,
                    "signals": len(signals),
                }

                for h in HORIZONS:
                    pnl = [(fwd[h] - close) for _, close, fwd in signals]
                    wins = [x for x in pnl if x > 0]
                    losses = [x for x in pnl if x < 0]
                    total = sum(pnl, Decimal("0"))
                    gross_profit = sum(wins, Decimal("0"))
                    gross_loss = abs(sum(losses, Decimal("0")))
                    pf = None if gross_loss == 0 else gross_profit / gross_loss
                    expectancy = None if not pnl else total / Decimal(len(pnl))
                    winrate = None if not pnl else Decimal(len(wins)) / Decimal(len(pnl))

                    result[f"expectancy_{h}"] = expectancy
                    result[f"pf_{h}"] = pf
                    result[f"winrate_{h}"] = winrate

                print(
                    "PARAM_ROW "
                    f"atr_threshold={atr_th} "
                    f"volume_mult={vol_mult} "
                    f"signals={result['signals']} "
                    f"expectancy_5={result['expectancy_5']} "
                    f"profit_factor_5={result['pf_5']} "
                    f"winrate_5={result['winrate_5']}"
                )

                if result["signals"] >= 5:
                    score = result["expectancy_5"] or Decimal("-999")
                    if best is None or score > best["score"]:
                        best = {"score": score, **result}

        if best:
            print(
                "BEST_ROW "
                f"atr_threshold={best['atr']} "
                f"volume_mult={best['vol']} "
                f"signals={best['signals']} "
                f"expectancy_5={best['expectancy_5']} "
                f"profit_factor_5={best['pf_5']} "
                f"winrate_5={best['winrate_5']}"
            )
            print("VERDICT=EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_HAS_CANDIDATE")
        else:
            print("VERDICT=EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_NO_CANDIDATE")

        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
