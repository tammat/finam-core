#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

SYMBOL = "SBER@MISX"
STRATEGY = "SBER_D1_SHADOW_SIGNAL_GENERATOR_V1"
TIMEFRAME = "D1"

SQL_D1_FROM_M5 = """
select
    date_trunc('day', ts) as day_ts,
    (array_agg(open order by ts asc))[1] as open,
    max(high) as high,
    min(low) as low,
    (array_agg(close order by ts desc))[1] as close,
    count(*) as m5_bars
from market_bars
where symbol=%s
  and timeframe='M5'
group by date_trunc('day', ts)
having count(*) >= 5
order by day_ts;
"""

INSERT = """
insert into sber_d1_shadow_accumulation_v1 (
    symbol,
    strategy,
    timeframe,
    signal_ts,
    side,
    entry_price,
    stop_price,
    take_price,
    shadow_only,
    runtime_allowed,
    execution_enabled,
    reason,
    raw_json
)
values (
    %(symbol)s,
    %(strategy)s,
    %(timeframe)s,
    %(signal_ts)s,
    %(side)s,
    %(entry_price)s,
    %(stop_price)s,
    %(take_price)s,
    true,
    false,
    false,
    %(reason)s,
    %(raw_json)s
)
on conflict(symbol, strategy, timeframe, signal_ts, side) do nothing;
"""

def dec(value) -> Decimal:
    return Decimal(str(value))

def main() -> int:
    print("=== SBER D1 SHADOW SIGNAL GENERATOR V1 ===")
    print("mode=shadow_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_D1_FROM_M5, (SYMBOL,))
            bars = cur.fetchall()

            if len(bars) < 5:
                print(
                    "SBER_D1_SHADOW_SIGNAL_SKIP "
                    f"reason=not_enough_bars bars={len(bars)} "
                    "bar_source=M5_AGGREGATED_TO_D1 "
                    "runtime_allow=0 execution_enabled=0"
                )
                print("SBER_D1_SHADOW_SIGNAL_GENERATOR_V1_OK")
                return 0

            closes = [dec(r["close"]) for r in bars]
            last = bars[-1]
            prev = bars[-2]

            last_close = dec(last["close"])
            prev_close = dec(prev["close"])
            last_high = dec(last["high"])
            last_low = dec(last["low"])

            ma5_period = min(5, len(closes))
            ma20_period = min(20, len(closes))

            ma5 = sum(closes[-ma5_period:]) / Decimal(str(ma5_period))
            ma20 = sum(closes[-ma20_period:]) / Decimal(str(ma20_period))

            low_history_mode = ma20_period < 20

            side = ""
            reason = ""

            if low_history_mode and last_close > ma5 and last_close > prev_close:
                side = "BUY"
                reason = "sber_d1_shadow_momentum_close_above_ma5:early_shadow_low_history"
            elif low_history_mode and last_close < ma5 and last_close < prev_close:
                side = "SELL"
                reason = "sber_d1_shadow_downtrend_close_below_ma5:early_shadow_low_history"
            elif last_close > ma5 > ma20 and last_close > prev_close:
                side = "BUY"
                reason = "sber_d1_shadow_momentum_close_above_ma5_ma20"
            elif last_close < ma5 < ma20 and last_close < prev_close:
                side = "SELL"
                reason = "sber_d1_shadow_downtrend_close_below_ma5_ma20"

            if not side:
                print(
                    "SBER_D1_SHADOW_SIGNAL_NO_SETUP "
                    f"symbol={SYMBOL} "
                    f"last_ts={last['day_ts']} "
                    f"close={last_close} "
                    f"ma5={ma5:.4f} "
                    f"ma20={ma20:.4f} "
                    f"bars={len(bars)} "
                    f"bar_source=M5_AGGREGATED_TO_D1 "
                    "runtime_allow=0 execution_enabled=0"
                )
                print("SBER_D1_SHADOW_SIGNAL_GENERATOR_V1_OK")
                return 0

            # Русский комментарий:
            # Shadow-уровни нужны только для последующей оценки качества сигнала.
            # Они не используются для выставления заявок.
            daily_range = max(last_high - last_low, Decimal("0.01"))

            if side == "BUY":
                entry_price = last_close
                stop_price = last_close - daily_range
                take_price = last_close + daily_range * Decimal("2")
            else:
                entry_price = last_close
                stop_price = last_close + daily_range
                take_price = last_close - daily_range * Decimal("2")

            payload = {
                "symbol": SYMBOL,
                "strategy": STRATEGY,
                "timeframe": TIMEFRAME,
                "signal_ts": str(last["day_ts"]),
                "side": side,
                "entry_price": str(entry_price),
                "stop_price": str(stop_price),
                "take_price": str(take_price),
                "ma5": str(ma5),
                "ma20": str(ma20),
                "ma5_period": ma5_period,
                "ma20_period": ma20_period,
                "bars": len(bars),
                "bar_source": "M5_AGGREGATED_TO_D1",
                "shadow_only": True,
                "runtime_allowed": False,
                "execution_enabled": False,
                "reason": reason,
            }

            cur.execute(
                INSERT,
                {
                    "symbol": SYMBOL,
                    "strategy": STRATEGY,
                    "timeframe": TIMEFRAME,
                    "signal_ts": last["day_ts"],
                    "side": side,
                    "entry_price": entry_price,
                    "stop_price": stop_price,
                    "take_price": take_price,
                    "reason": reason,
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )
            inserted = cur.rowcount
        conn.commit()

    print(
        "SBER_D1_SHADOW_SIGNAL_ROW "
        f"symbol={SYMBOL} "
        f"strategy={STRATEGY} "
        f"timeframe={TIMEFRAME} "
        f"side={side} "
        f"entry={entry_price:.4f} "
        f"stop={stop_price:.4f} "
        f"take={take_price:.4f} "
        f"ma5={ma5:.4f} "
        f"ma20={ma20:.4f} "
        f"bars={len(bars)} "
        "bar_source=M5_AGGREGATED_TO_D1 "
        f"inserted={inserted} "
        "runtime_allow=0 execution_enabled=0"
    )
    print("SBER_D1_SHADOW_SIGNAL_GENERATOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
