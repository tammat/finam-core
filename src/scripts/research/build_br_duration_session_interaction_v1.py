from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import timezone

import psycopg


KEEP_REGIME = "LOW_IMPULSE"
KEEP_TREND = "down"
KEEP_VOLATILITY = "high"


@dataclass(frozen=True)
class Metrics:
    trades: int
    wins: int
    losses: int
    net_pnl: float
    expectancy: float
    profit_factor: float
    winrate: float


def classify_session(hour: int) -> str:
    if 0 <= hour < 10:
        return "ASIA"
    if 10 <= hour < 15:
        return "EUROPE"
    if 15 <= hour < 19:
        return "US_OPEN"
    return "US_LATE"


def duration_bucket(minutes: float) -> str:
    if minutes < 5:
        return "SCALP_LT_5M"
    if minutes < 15:
        return "FAST_5_15M"
    if minutes < 60:
        return "INTRADAY_15_60M"
    if minutes < 240:
        return "SWING_1_4H"
    return "LONG_GT_4H"


def calc_metrics(pnls: list[float]) -> Metrics:
    trades = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    losses = sum(1 for x in pnls if x <= 0)
    net_pnl = sum(pnls)
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    expectancy = net_pnl / trades if trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0
    winrate = wins / trades if trades else 0.0
    return Metrics(trades, wins, losses, net_pnl, expectancy, profit_factor, winrate)


def status_for(metrics: Metrics) -> str:
    if metrics.trades < 5:
        return "LOW_SAMPLE"
    if metrics.profit_factor >= 1.20 and metrics.expectancy > 0:
        return "CONFIRMED"
    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
        return "WATCH"
    return "FAILED"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        COALESCE(tcs.exit_ts, tcs.entry_ts) AS ts,
        EXTRACT(EPOCH FROM (tcs.exit_ts - tcs.entry_ts)) / 60.0 AS duration_minutes,
        a.pnl
    FROM trade_context_snapshots tcs
    JOIN trade_attribution_v2 a
      ON a.closed_trade_id = tcs.closed_trade_id
    WHERE tcs.symbol = 'BRM6@RTSX'
      AND tcs.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND a.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND tcs.context_quality = 'FULL'
      AND tcs.regime = %(regime)s
      AND tcs.trend = %(trend)s
      AND tcs.volatility = %(volatility)s
      AND tcs.entry_ts IS NOT NULL
      AND tcs.exit_ts IS NOT NULL
    ORDER BY COALESCE(tcs.exit_ts, tcs.entry_ts), tcs.closed_trade_id;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"regime": KEEP_REGIME, "trend": KEEP_TREND, "volatility": KEEP_VOLATILITY})
            rows = cur.fetchall()

    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)

    for ts, duration_minutes, pnl in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        session = classify_session(int(ts.hour))
        bucket = duration_bucket(float(duration_minutes or 0.0))
        grouped[(bucket, session)].append(float(pnl or 0.0))

    print("BR_DURATION_SESSION_INTERACTION_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print(f"total_trades={len(rows)}")
    print("duration_bucket | session | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")

    confirmed = 0
    failed = 0

    for (bucket, session), pnls in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1])):
        metrics = calc_metrics(pnls)
        status = status_for(metrics)

        if status == "CONFIRMED":
            confirmed += 1
        if status == "FAILED":
            failed += 1

        print(
            f"{bucket} | {session} | {metrics.trades} | {metrics.wins} | {metrics.losses} | "
            f"{metrics.winrate:.6f} | {metrics.net_pnl:.6f} | {metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | {status}"
        )

    if confirmed > 0 and failed > 0:
        verdict = "EDGE_CONCENTRATED_WITH_TOXIC_BUCKETS"
    elif confirmed > 0:
        verdict = "EDGE_CONCENTRATED"
    else:
        verdict = "NO_CONFIRMED_DURATION_SESSION_EDGE"

    print("SUMMARY")
    print(f"confirmed_buckets={confirmed}")
    print(f"failed_buckets={failed}")
    print(f"verdict={verdict}")
    print(f"BR_DURATION_SESSION_INTERACTION_V1_OK buckets={len(grouped)} verdict={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
