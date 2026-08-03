from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "MARKET_EVENT_REACTION_SHADOW_V1"
HORIZONS = {15: 3, 30: 6, 60: 12}


def direction_code(return_pct: Decimal, flat_threshold: Decimal = Decimal("0.0001")) -> str:
    if return_pct > flat_threshold:
        return "UP"
    if return_pct < -flat_threshold:
        return "DOWN"
    return "FLAT"


def main() -> int:
    written = 0
    pending = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT e.event_code,e.starts_at,e.symbol_patterns
              FROM analytics.market_event_risk_v1 e
              JOIN analytics.market_event_confirmation_v1 c USING(event_code)
              WHERE c.confirmation_status='CONFIRMED'
                AND e.starts_at>=clock_timestamp()-interval '14 days'
              ORDER BY starts_at""")
            for event in cursor.fetchall():
                for symbol in event["symbol_patterns"]:
                    if "*" in symbol:
                        continue
                    cursor.execute("""SELECT ts,open,high,low,close,coalesce(volume,0) volume
                      FROM market_bars WHERE symbol=%s AND timeframe='M5'
                        AND ts>=%s AND ts+interval '5 minutes'<=clock_timestamp()
                      ORDER BY ts LIMIT 12""", (symbol,event["starts_at"]))
                    bars = cursor.fetchall()
                    if not bars:
                        pending += len(HORIZONS)
                        continue
                    first_ts = bars[0]["ts"]
                    cursor.execute("""SELECT close FROM market_bars WHERE symbol=%s AND timeframe='M5'
                      AND ts<%s ORDER BY ts DESC LIMIT 1""", (symbol,first_ts))
                    prior_close_row = cursor.fetchone()
                    cursor.execute("""SELECT high,low,coalesce(volume,0) volume FROM market_bars
                      WHERE symbol=%s AND timeframe='M5' AND ts<%s ORDER BY ts DESC LIMIT 20""",
                      (symbol,first_ts))
                    prior = cursor.fetchall()
                    if not prior_close_row or not prior:
                        pending += len(HORIZONS)
                        continue
                    baseline = Decimal(str(prior_close_row["close"]))
                    atr_rows = prior[:14]
                    atr = sum((Decimal(str(row["high"]))-Decimal(str(row["low"])) for row in atr_rows), Decimal("0"))/Decimal(len(atr_rows))
                    baseline_volume_rows = [Decimal(str(row["volume"])) for row in prior if row["volume"]]
                    baseline_volume = (sum(baseline_volume_rows,Decimal("0"))/Decimal(len(baseline_volume_rows))
                                       if baseline_volume_rows else Decimal("0"))
                    for horizon,index in HORIZONS.items():
                        if len(bars)<index:
                            pending += 1
                            continue
                        horizon_bars=bars[:index]; close=Decimal(str(horizon_bars[-1]["close"]))
                        return_pct=(close-baseline)/baseline if baseline else Decimal("0")
                        move_atr=(close-baseline)/atr if atr else None
                        mean_volume=sum((Decimal(str(row["volume"])) for row in horizon_bars),Decimal("0"))/Decimal(len(horizon_bars))
                        relative_volume=mean_volume/baseline_volume if baseline_volume else None
                        cursor.execute("""INSERT INTO analytics.market_event_reaction_shadow_v1(
                          event_code,symbol,event_ts,first_market_bar_ts,horizon_minutes,
                          baseline_close,horizon_close,return_pct,move_atr,relative_volume,
                          direction_code,directional_signal,source_version)
                          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s)
                          ON CONFLICT(event_code,symbol,horizon_minutes) DO UPDATE SET
                           horizon_close=excluded.horizon_close,return_pct=excluded.return_pct,
                           move_atr=excluded.move_atr,relative_volume=excluded.relative_volume,
                           direction_code=excluded.direction_code,calculated_at=clock_timestamp()""",
                          (event["event_code"],symbol,event["starts_at"],first_ts,horizon,
                           baseline,close,return_pct,move_atr,relative_volume,
                           direction_code(return_pct),VERSION))
                        written += cursor.rowcount
    print(f"written={written} pending={pending}")
    print("directional_signal=0 paper_changed=0 real_changed=0")
    print(f"VERDICT={VERSION}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
