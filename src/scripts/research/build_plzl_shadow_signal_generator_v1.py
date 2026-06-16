#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

SYMBOL = "PLZL@MISX"
STRATEGY = "PLZL_SHADOW_SIGNAL_GENERATOR_V1"
TIMEFRAME = "D1"

DDL = """
CREATE TABLE IF NOT EXISTS plzl_shadow_accumulation_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_ts TIMESTAMPTZ,
    side TEXT NOT NULL,
    entry_price NUMERIC,
    stop_price NUMERIC,
    take_price NUMERIC,
    reason TEXT NOT NULL DEFAULT '',
    shadow_only BOOLEAN NOT NULL DEFAULT true,
    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
    execution_enabled BOOLEAN NOT NULL DEFAULT false,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_plzl_shadow_accumulation_v1_signal
ON plzl_shadow_accumulation_v1(symbol, strategy, timeframe, signal_ts, side);
"""

LOAD_BARS = """
select
    ts,
    open,
    high,
    low,
    close,
    volume
from market_bars
where symbol=%s
  and timeframe=%s
order by ts desc
limit 30;
"""

LOAD_D1_FROM_M5 = """
with m5 as (
    select
        ts::date as trade_date,
        ts,
        open,
        high,
        low,
        close,
        volume,
        row_number() over (partition by ts::date order by ts asc) as rn_first,
        row_number() over (partition by ts::date order by ts desc) as rn_last
    from market_bars
    where symbol=%s
      and timeframe='M5'
),
daily as (
    select
        trade_date,
        min(ts) as ts,
        max(high) as high,
        min(low) as low,
        sum(volume) as volume,
        max(open) filter (where rn_first=1) as open,
        max(close) filter (where rn_last=1) as close
    from m5
    group by trade_date
)
select
    ts,
    open,
    high,
    low,
    close,
    volume
from daily
order by ts desc
limit 30;
"""

INSERT_SIGNAL = """
insert into plzl_shadow_accumulation_v1 (
    symbol,
    strategy,
    timeframe,
    signal_ts,
    side,
    entry_price,
    stop_price,
    take_price,
    reason,
    shadow_only,
    runtime_allowed,
    execution_enabled,
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
    %(reason)s,
    true,
    false,
    false,
    %(raw_json)s
)
on conflict (symbol, strategy, timeframe, signal_ts, side) do nothing;
"""

def q(x) -> Decimal:
    return Decimal(str(x))

def main() -> int:
    print("=== PLZL SHADOW SIGNAL GENERATOR V1 ===", flush=True)
    print("mode=shadow_only", flush=True)
    print("runtime_allow=0", flush=True)
    print("execution_enabled=0", flush=True)

    inserted = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(LOAD_BARS, (SYMBOL, TIMEFRAME))
            bars = cur.fetchall()
            bar_source = "D1"

            if len(bars) < 5:
                cur.execute(LOAD_D1_FROM_M5, (SYMBOL,))
                bars = cur.fetchall()
                bar_source = "M5_AGGREGATED_TO_D1"

            bars = list(reversed(bars))

            if len(bars) < 5:
                print(
                    "PLZL_SHADOW_SIGNAL_SKIP "
                    f"reason=not_enough_bars bars={len(bars)} "
                    f"bar_source={bar_source} "
                    "runtime_allow=0 execution_enabled=0",
                    flush=True,
                )
                conn.commit()
                print("PLZL_SHADOW_SIGNAL_GENERATOR_V1_OK", flush=True)
                return 0

            closes = [q(b["close"]) for b in bars]
            last = bars[-1]
            last_close = q(last["close"])
            prev_close = q(bars[-2]["close"])

            ma5_period = min(5, len(closes))
            ma20_period = min(20, len(closes))

            ma5 = sum(closes[-ma5_period:]) / Decimal(str(ma5_period))
            ma20 = sum(closes[-ma20_period:]) / Decimal(str(ma20_period))

            side = ""
            reason = ""

            low_history_mode = ma20_period < 20

            if low_history_mode and last_close > ma5 and last_close > prev_close:
                side = "BUY"
                reason = "plzl_shadow_momentum_d1_close_above_ma5:early_shadow_low_history"
            elif low_history_mode and last_close < ma5 and last_close < prev_close:
                side = "SELL"
                reason = "plzl_shadow_downtrend_d1_close_below_ma5:early_shadow_low_history"
            elif last_close > ma5 > ma20 and last_close > prev_close:
                side = "BUY"
                reason = "plzl_shadow_momentum_d1_close_above_ma5_ma20"
            elif last_close < ma5 < ma20 and last_close < prev_close:
                side = "SELL"
                reason = "plzl_shadow_downtrend_d1_close_below_ma5_ma20"

            if not side:
                print(
                    "PLZL_SHADOW_SIGNAL_NO_SETUP "
                    f"symbol={SYMBOL} "
                    f"last_ts={last['ts']} "
                    f"close={last_close} "
                    f"ma5={ma5:.4f} "
                    f"ma20={ma20:.4f} "
                    "runtime_allow=0 execution_enabled=0",
                    flush=True,
                )
                conn.commit()
                print("PLZL_SHADOW_SIGNAL_GENERATOR_V1_OK", flush=True)
                return 0

            risk_unit = abs(last_close - ma20)
            if risk_unit <= 0:
                risk_unit = last_close * Decimal("0.015")

            if side == "BUY":
                stop_price = last_close - risk_unit
                take_price = last_close + risk_unit * Decimal("2")
            else:
                stop_price = last_close + risk_unit
                take_price = last_close - risk_unit * Decimal("2")

            payload = {
                "symbol": SYMBOL,
                "strategy": STRATEGY,
                "timeframe": TIMEFRAME,
                "signal_ts": str(last["ts"]),
                "side": side,
                "entry_price": str(last_close),
                "stop_price": str(stop_price),
                "take_price": str(take_price),
                "ma5": str(ma5),
                "ma20": str(ma20),
                "shadow_only": True,
                "runtime_allowed": False,
                "execution_enabled": False,
                "reason": reason,
                "bar_source": bar_source,
            }

            cur.execute(
                INSERT_SIGNAL,
                {
                    "symbol": SYMBOL,
                    "strategy": STRATEGY,
                    "timeframe": TIMEFRAME,
                    "signal_ts": last["ts"],
                    "side": side,
                    "entry_price": str(last_close),
                    "stop_price": str(stop_price),
                    "take_price": str(take_price),
                    "reason": reason,
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )
            inserted = cur.rowcount
        conn.commit()

    print(
        "PLZL_SHADOW_SIGNAL_ROW "
        f"symbol={SYMBOL} strategy={STRATEGY} timeframe={TIMEFRAME} "
        f"side={side} entry={last_close} stop={stop_price:.4f} take={take_price:.4f} "
        f"bar_source={bar_source} "
        f"inserted={inserted} runtime_allow=0 execution_enabled=0",
        flush=True,
    )
    print("PLZL_SHADOW_SIGNAL_GENERATOR_V1_OK", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
